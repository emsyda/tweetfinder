from scripts.fetch_and_save_tweets import (TweetFetcher, get_tweet)
from langchain.document_loaders import CSVLoader
#from langchain.docstore.document import Document
#from langchain.llms import OpenAI
from langchain.indexes import VectorstoreIndexCreator
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
import argparse
import re
import os
import json

PERSIST_DIRECTORY = 'data/.vectorbase'
PERSIST_DIRECTORY_TEST = '.test/data/.vectorbase'
os.makedirs(PERSIST_DIRECTORY, exist_ok=True)
os.makedirs(PERSIST_DIRECTORY_TEST, exist_ok=True)


class EmbeddingsGenerator:
    def __init__(self, screen_name, openai_api_key, *, test=False):
        if openai_api_key is None:
            raise ValueError("openai_api_key must be set")
        self.screen_name = screen_name
        self.collection_name = screen_name.lower()
        self.openai_api_key = openai_api_key
        self.csv_path = TweetFetcher.get_csv_path(screen_name, test=test)
        self.db_path = PERSIST_DIRECTORY_TEST if test else PERSIST_DIRECTORY
        self.doc_loader = CSVLoader(self.csv_path, csv_args={'delimiter': ',', 'quotechar': '"'})
        self.load_documents()
        self.load_vectorbase()
        self.generate_embeddings()
        #print(self.documents)
        #self.llm = OpenAI()
        #self.index_creator = VectorstoreIndexCreator(vectorstore_cls=Chroma)

    def load_documents(self):
        docs = self.doc_loader.load()
        for doc in docs:
            # . matches any character except newline, re.DOTALL adds newline to the matchable characters
            text = re.search(r"text: (.+?)\nis_retweet: ", doc.page_content, re.DOTALL).group(1)
            id = re.search(r"id: (.+?)\n", doc.page_content, re.DOTALL).group(1)
            doc.page_content = text
            doc.metadata['status_id'] = id
        self.documents = docs
        return docs
    

    def generate_embeddings(self):
        self._generate_embeddings_add_to_existing()
    
    
    def _generate_embeddings_add_to_existing(self):
        self.load_vectorbase()
        ids = [x.metadata['status_id'] for x in self.documents]
        # _collection.get() result:
        # {'ids': [], 'embeddings': None, 'documents': [], 'metadatas': []}
        existing_ids = self.vectordb._collection.get(ids)['ids']
        new_docs = [x for x in self.documents if x.metadata['status_id'] not in existing_ids]
        new_ids = [x.metadata['status_id'] for x in new_docs]
        if new_docs:
            print(f"Adding {len(new_docs)} new documents out of {len(self.documents)} total documents to user '{self.collection_name}' vectorbase")
        if new_docs:
            self.vectordb.add_documents(new_docs, ids=new_ids)
            self.vectordb.persist()
    

    def _generate_embeddings_from_scratch(self):
        #self.index = self.index_creator.from_loaders([self.loader])
        ids = [x.metadata['status_id'] for x in self.documents]
        # Will raise error if an id already exists
        self.vectordb = Chroma.from_documents(self.documents, embedding=OpenAIEmbeddings(openai_api_key=self.openai_api_key),
                                              persist_directory=self.db_path, collection_name=self.collection_name, ids=ids)
        self.vectordb.persist()


    def load_vectorbase(self):
        #self.index = VectorstoreIndexCreator().parse_file(
        if getattr(self, 'vectordb', None) is None:
            self.vectordb = Chroma(persist_directory=self.db_path,
                                   embedding_function=OpenAIEmbeddings(openai_api_key=self.openai_api_key),
                                   collection_name=self.collection_name)
    
    @staticmethod
    def clear(screen_name, openai_api_key, *, test=False):
        if openai_api_key is None:
            raise ValueError("openai_api_key must be set") # `None` may mess up the existing vb due to using default-embedding on the existing one
        db_path = PERSIST_DIRECTORY_TEST if test else PERSIST_DIRECTORY
        vectordb = Chroma(persist_directory=db_path,
                          embedding_function=OpenAIEmbeddings(openai_api_key=openai_api_key),
                          collection_name=screen_name.lower())
        vectordb.delete_collection()


    def query(self, query, k=10, filter: dict[str, str] = None):
        #return self.index.query(query, k=k)
        return self.vectordb.similarity_search(query, k=k, filter=filter)


def query(screen_name, qry, k=10, *, test=False, embeddings_generator=None, tweets=None, openai_api_key=None):
        if embeddings_generator is None:
            embeddings_generator = EmbeddingsGenerator(screen_name, test=test, openai_api_key=openai_api_key)

        # filter = {'status_id': '123'}
        # filter = {'status_id': {'$gt', '123'}}
        # filter = {'$or': [{'status_id': '123'}, {'status_id': '456'}]}
        filter = None
        if tweets and len(tweets) >= 2:
            filter = {'$or':[{'status_id': x['id']} for x in tweets]}
        elif tweets:
            filter = {'status_id': tweets[0]['id']} # error is raised by chromadb if we use $or with 1 option
        
        docs = embeddings_generator.query(qry, k, filter)
        if not docs:
            return []

        if tweets is None:
            tweets = TweetFetcher(None, screen_name, test=test, user_id='123').tweets
        
        top_tweets = []
        for doc in docs:
            try:
                top_tweets.append(
                    TweetFetcher._get_tweet(tweets, doc.metadata['status_id']))
            except ValueError:
                # Tweet is not among the provided tweets (filtered out)
                pass
        
        return top_tweets


def main():
    import logging
    logging.basicConfig(level='DEBUG')

    parser = argparse.ArgumentParser()

    # Required argument
    parser.add_argument("screen_name", help="Twitter screen name")

    parser.add_argument("--test", action="store_true", help="Execute in test mode")

    parser.add_argument("--command", '-c', help="one of: ['run/clear']", choices=['run','clear'], default=None)
    parser.add_argument('-q', "--query", help="Search for a tweet by text query", default=None)
    parser.add_argument('-k', type=int, help="Number of tweets to be queried", default=10)

    parser.add_argument("--openai_api_key", '--key', help="OpenAI API key", required=True) # `None` may mess up the existing database

    args = parser.parse_args()
    print(args)

    if args.command == 'clear':
        EmbeddingsGenerator.clear(args.screen_name, args.openai_api_key, test=args.test)
        return

    emb_gen = EmbeddingsGenerator(args.screen_name, args.openai_api_key, test=args.test)
    #print(emb_gen.documents)
    
    #docs = emb_gen.query("give to the poor", 1)
    #print(docs)

    if args.query:
        tweets = query(args.screen_name, args.query, k=args.k, test=args.test, embeddings_generator=emb_gen)
        print(f"\nTop {args.k} tweets (desc. match):")
        for tweet in tweets:
            print(f"{json.dumps(tweet)}")

    return emb_gen


if __name__ == '__main__':
    main()

"""
# Loaded documents example (1 row only)
[Document(page_content="id: 1302753476540162049\ntext: @ESYudkowsky Nothing new, same kind of stuff I've been writing about for years and that's been tough for us to get on the same page about. Basic plan is to build tools to help the evaluator, trying to reach the point where the evaluator is epistemically efficient relative to the model.",
          metadata={'source': '.test/data/tweets_paulfchristiano.csv', 'row': 0, 'status_id': '1302753476540162049'})]

# _collection.get(ids) result
{
    'ids': ['1302753476540162049'],
    'embeddings': None,
    'documents': ["@ESYudkowsky Nothing new, same kind of stuff I've been writing about for years and that's been tough for us to get on the same page about. Basic plan is to build tools to help the evaluator, trying to reach the point where the evaluator is epistemically efficient relative to the model."],
    'metadatas': [{'source': '.test/data/tweets_paulfchristiano.csv', 'row': 0, 'status_id': '1302753476540162049'}]
}          
"""

