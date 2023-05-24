# if $1 or $2 is not defined, exit
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./setup.sh <backend URI local> <backend URI global>"
    exit 1
fi
echo " * Backend URIs: $1 $2"

# $BACKEND_URI must be escaped with \$, not $$
sed "s|\$BACKEND_URI_LOCAL|$1|g" /etc/nginx/conf.d/template.conf > /etc/nginx/conf.d/default.conf
sed -i "s|\$BACKEND_URI_GLOBAL|$2|g" /etc/nginx/conf.d/default.conf
echo " * Nginx config file: " && cat /etc/nginx/conf.d/default.conf

# remove the template (otherwise nginx will default to this)
rm /etc/nginx/conf.d/template.conf
