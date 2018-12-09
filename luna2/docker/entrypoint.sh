#!/bin/bash

set -x
set -e

function create_mongo_logs() {
    if [ -d /logs/mongo ]; then
        return
    fi
    mkdir -p /logs/mongo
    touch /logs/mongo/mongod.log
    chown mongod:mongod -R /logs/mongo
    chmod 640 /logs/mongo/mongod.log
}

function create_mongo_data() {
    if [ -z ${MONGODB_ADMIN_PASSFILE} ]; then
        export MONGODB_ADMIN_PASSFILE=/data/mongo/admin.password
    fi
    if [ -d /data/mongo ]; then
        if [ -n ${MONGODB_ADMIN_PASS} ]; then
            create_mongorc_js
        fi
        if [ -f ${MONGODB_ADMIN_PASSFILE} ]; then
            export MONGODB_ADMIN_PASS=$(cat ${MONGODB_ADMIN_PASSFILE})
            create_mongorc_js
        fi
        return
    fi
    mkdir -p /data/mongo
    chown mongod:mongod -R /data/mongo
    if [ -z ${MONGODB_ADMIN_PASS} ]; then
        MONGODB_ADMIN_PASS=$(openssl rand -base64 32)
        mkdir -p $(dirname ${MONGODB_ADMIN_PASSFILE})
        touch ${MONGODB_ADMIN_PASSFILE}
        chmod 400 ${MONGODB_ADMIN_PASSFILE}
        echo ${MONGODB_ADMIN_PASS} > ${MONGODB_ADMIN_PASSFILE}
        export MONGODB_ADMIN_PASS
    fi
    secure_mongo
    create_mongorc_js
}

function create_mongorc_js() {
    echo "db.getSiblingDB(\"admin\").auth(\"root\", \"${MONGODB_ADMIN_PASS}\")" > /root/.mongorc.js
}

function secure_mongo() {
    su -c "/bin/mongod --config /etc/mongod.conf --fork --noauth" mongod -s /bin/bash
    wait_mongo_online
    cat << EOF | mongo --norc
use admin
db.createUser(
  {
    user: "root",
    pwd: "${MONGODB_ADMIN_PASS}",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" }, "readWriteAnyDatabase" ]
  }
)
EOF
    mongod --config /etc/mongod.conf --shutdown
}

function wait_mongo_online() {
    TRIES=60
    while ! echo "{ping: 1}" | mongo --quiet; do
        sleep 1
        TRIES=$(( ${TRIES}-1 ))
        if [ ${TRIES} -le 0 ]; then
            echo 'Timeout waining MongoDB to come up'
            exit 255
        fi
    done
}

function create_luna_config() {
    if [ -z ${LUNA_DB_NAME} ]; then
        export LUNA_DB_NAME=luna
    fi
    if [ -z ${LUNA_DB_USER} ]; then
        export LUNA_DB_USER=luna
    fi
    if [ -z ${LUNA_DATASTORE} ]; then
        export LUNA_DATASTORE=/data/luna
    fi
    mkdir -p ${LUNA_DATASTORE}/{boot,torrents}
    chown luna: ${LUNA_DATASTORE}
    chown luna: ${LUNA_DATASTORE}/{boot,torrents}
    if [ -z ${LUNA_DB_PASSFILE} ]; then
        export LUNA_DB_PASSFILE=${LUNA_DATASTORE}/db.pass
    fi
    if [ ! -f ${LUNA_DB_PASSFILE} ]; then
        MONGODB_LUNA_PASS=$(openssl rand -base64 32)
        mkdir -p $(dirname ${LUNA_DB_PASSFILE})
        echo "${MONGODB_LUNA_PASS}" > ${LUNA_DB_PASSFILE}
        chmod 400 ${LUNA_DB_PASSFILE}
        chown luna: ${LUNA_DB_PASSFILE}
        add_luna_user_to_mongo
    else
        MONGODB_LUNA_PASS=$(cat ${LUNA_DB_PASSFILE})
    fi
    if [ -z ${LUNA_REST_TOKENFILE} ]; then
        export LUNA_REST_TOKENFILE=${LUNA_DATASTORE}/rest.token
    fi
    if [ ! -f ${LUNA_REST_TOKENFILE} ]; then
        LUNA_REST_TOKEN=$(openssl rand -base64 32)
        mkdir -p $(dirname ${LUNA_REST_TOKENFILE})
        echo "${LUNA_REST_TOKEN}" > ${LUNA_REST_TOKENFILE}
        chmod 400 ${LUNA_REST_TOKENFILE}
        chown luna: ${LUNA_REST_TOKENFILE}
    else
        LUNA_REST_TOKEN=$(cat ${LUNA_REST_TOKENFILE})
    fi
    mkdir -p /etc/luna
    touch /etc/luna/lunad.conf
    chmod 400 /etc/luna/lunad.conf
    chown luna: /etc/luna/lunad.conf
    cat << EOF > /etc/luna/lunad.conf
db:
  server: "localhost"
  authdb: "${LUNA_DB_NAME}"
  user: "${LUNA_DB_USER}"
  password: "${MONGODB_LUNA_PASS}"
auth:
  token: "${LUNA_REST_TOKEN}"
store:
  path: "${LUNA_DATASTORE}"
EOF
}

function add_luna_user_to_mongo() {
    su -c "/bin/mongod --config /etc/mongod.conf --fork --noauth" mongod -s /bin/bash
    wait_mongo_online
    cat << EOF | mongo --norc
use luna
db.createUser(
  {
    user: "${LUNA_DB_USER}",
    pwd: "${MONGODB_LUNA_PASS}",
    roles: [ { role: "dbOwner", db: "${LUNA_DB_NAME}" } ]
  }
)
EOF
    mongod --config /etc/mongod.conf --shutdown
}

function create_nginx_config() {
    if [ -z ${GUNICORN_PORT} ]; then
        export GUNICORN_PORT=6001
    fi
    if [ -z ${NGINX_BIND_PORT} ]; then
        export NGINX_BIND_PORT=7050
    fi
    if [ -z ${LUNA_DATASTORE} ]; then
        export LUNA_DATASTORE=/data/luna
    fi
    cp -f /etc/nginx/nginx.conf.in /etc/nginx/nginx.conf
    sed -i -e "s/__GUNICORN_PORT__/${GUNICORN_PORT}/g" /etc/nginx/nginx.conf
    sed -i -e "s/__NGINX_BIND_PORT__/${NGINX_BIND_PORT}/g" /etc/nginx/nginx.conf
    sed -i -e "s|__LUNA_DATASTORE__|${LUNA_DATASTORE}|g" /etc/nginx/nginx.conf
    mkdir -p /logs/nginx
    chown nginx: /logs/nginx
}

create_mongo_logs
create_mongo_data
create_luna_config
create_nginx_config
supervisord -c /etc/supervisord.conf
