#!/bin/sh -x

django-admin startproject server .
rm ./server/settings.py
rm ./server/urls.py
cp ./settings/urls-production.py ./server/urls.py

new_version=$(head -n 1 ./settings/settings-production.py)
# We check if the settings file already exist and is the same version.
if [ -e /root/.config/joplin-vieweb/settings.py ]
then
    # settings file exists. Let's check it's the same version as new. If not, we remove current settings.py to force a new one.
    current_version=$(head -n 1 /root/.config/joplin-vieweb/settings.py)
    if [[ "${current_version}" != "${new_version}" ]]
    then
        echo "settings file already exists, but in previous version (${current_version}), we delete it."
        rm /root/.config/joplin-vieweb/settings.py
        sync  
    else
        echo "settings file already exists, in the last version (${current_version}), we use it."
    fi
fi

if [ ! -e /root/.config/joplin-vieweb/settings.py ]
then
    echo "Let's create django settings files (origins: ${ORIGINS}) in version ${new_version}"
    cp ./settings/settings-production.py /root/.config/joplin-vieweb/settings.py
    secret_key=$(python -c "from django.core.management.utils import get_random_secret_key;print(get_random_secret_key())")
    sed -i "s/secret_key_placeholder/$secret_key/" /root/.config/joplin-vieweb/settings.py
    sed -i "s~ORIGINS_PLACEHOLDER~${ORIGINS}~" /root/.config/joplin-vieweb/settings.py
fi
ln -s /root/.config/joplin-vieweb/settings.py ./settings/settings.py
export DJANGO_SETTINGS_MODULE=settings.settings
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py initadmin
nginx -g 'daemon on;'
daphne -p 8001 server.asgi:application
