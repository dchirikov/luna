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
    if [ -d /data/mongo ]; then
        if [ -n ${MONGODB_ADMIN_PASS} ]; then
            create_mongorc_js
        fi
        if [ -f /data/mongo/admin.password ]; then
            export MONGODB_ADMIN_PASS=$(cat /data/mongo/admin.password)
            create_mongorc_js
        fi
        return
    fi
    mkdir -p /data/mongo
    chown mongod:mongod -R /data/mongo
    if [ -z ${MONGODB_ADMIN_PASS} ]; then
        MONGODB_ADMIN_PASS=$(openssl rand -base64 32)
        touch /data/mongo/admin.password
        chmod 400 /data/mongo/admin.password
        echo ${MONGODB_ADMIN_PASS} > /data/mongo/admin.password
        export MONGODB_ADMIN_PASS
    fi
    secure_mongo
    create_mongorc_js
}

function create_mongorc_js() {
    echo "db.getSiblingDB(\"admin\").auth(\"root\", \"${MONGODB_ADMIN_PASS}\")" > /root/.mongorc.js
}

function secure_mongo() {
    su -c "/bin/mongod --config /conf/mongo/mongod.conf --fork --noauth" mongod -s /bin/bash
    wait_mongo_online
    cat << EOF | mongo
use admin
db.createUser(
  {
    user: "root",
    pwd: "${MONGODB_ADMIN_PASS}",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" }, "readWriteAnyDatabase" ]
  }
)
EOF
    mongod --config /conf/mongo/mongod.conf --shutdown
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

create_mongo_logs
create_mongo_data
supervisord -c /etc/supervisord.conf
