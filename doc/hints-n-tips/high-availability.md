# Using luna in an HA configuration

## MongoDB config

By default MongoDB listens only loopback interface and provides no credentials checking.

To set up a replica set, `/etc/mongod.conf` needs to be updated

Sample config:

```
bind_ip = 127.0.0.1,10.30.255.254
replSet = luna
```

Then mongod needs to be restarted:

```
systemctl restart mongod
```

Using mongo CLI, setup a replica set:

```
rs.initiate()
```

Then restart mongod and back to CLI

- Add root user:

```
use admin
db.createUser({user: "root", pwd: "<password>", roles: [ { role: "root", db: "admin" } ]})
```
edit config mongod to enable auth:
```
auth = true
```
restart mongod:
```
systemctl restart mongod
```
Enter to mongo shell:
```
mongo -u root -p <password> --authenticationDatabase admin
```
Create user for Luna:
```
use luna
db.createUser({user: "luna", pwd: "<password>", roles: [{role: "dbOwner", db: "luna"}]})
```
Now we are ready to create config file for connection:
```
cat << EOF > /etc/luna.conf
[MongoDB]
replicaset=luna
server=localhost
authdb=luna
user=luna
password=<password>
EOF
```
## Configure luna for HA

Consider you have:

|IP                       | Name      |
|------------------------:|:----------|
|           10.30.255.251 |   master1 |
|           10.30.255.252 |   master2 |
|(floating) 10.30.255.254 |   master  |

```
openssl rand -base64 741 > /etc/mongo.key
chown mongodb: /etc/mongo.key
chmod 400 /etc/mongo.key
```
Add parameter to  /etc/mongod.conf
```
keyFile = /etc/mongo.key
```
Copy files to other master
```
scp -pr /etc/mongo.key 10.30.255.252:/etc/
scp /etc/mongod.conf 10.30.255.252:/etc/
```

Edit mongod.conf to to change the ip address there:
```
sed -i -e 's/10.30.255.251/10.30.255.252/' /etc/mongod.conf
```
Restart mongo instances on both servers:
```
systemctl restart mongod
```
In mongo shell add another member:
```
rs.add("10.30.255.252")
```
Then restart mongod instance on other master.

Check status:
```
luna:PRIMARY> rs.status()
```

## (Optional) Adding a mongodb arbiter

For HA setups with two nodes, the following configuration is suggested:

On each node, you will have MongoDB with full data sets ready to handle data requests. As we have only 2 instances, in case one fails, the live instance will decide that a split-brain situation has occured and will demote itself to secondary and will refuse to handle requests.

To avoid such a situation, we need to have a tie-breaker - the arbiter. It is a tiny service (in terms of memory footprint and service logic) which adds one vote to the master election in a mongodb replicaset.
We will have a copy of the arbiter on the two nodes. And we will use pacemaker to bring one and only one copy of the arbiter online. Pacemaker should have STONITH configured.
This way even is the pacemaker cluster is down the regular mongodb instances will still have 2 votes out of 3 and service will still be available.


Copy mongod config:
```
cp /etc/mongod.conf /etc/mongod-arbiter.conf
```

Change the following:

```
bind_ip = 127.0.0.1,10.30.255.254   # 255.254 will be cluster (floating) ip here
port = 27018                        # non standart port not to conflict with other MongoDB instancess
pidfilepath = /var/run/mongodb-arbiter/mongod.pid
logpath = /var/log/mongodb/mongod-arbiter.log
unixSocketPrefix = /var/run/mongodb-arbiter
dbpath = /var/lib/mongodb-arbiter
nojournal = true                    # disable journal in order to reduce amount of data in dbpath
noprealloc = true                   # disable noprealloc for the same reason
smallfiles = true                   # same considerations
```

Create an environmental file:

```
cat << EOF > /etc/sysconfig/mongod-arbiter
> OPTIONS="--quiet -f /etc/mongod-arbiter.conf"
> EOF
```

For initialization you need to bring the floating IP up on one of the nodes:

```
ip a add 10.30.255.254/16 dev eth1
```

Create a systemd unit for the arbiter:

```
cat << EOF > /etc/systemd/system/mongod-arbiter.service
[Unit]
Description=Arbiter for MongoDB
After=syslog.target network.target

[Service]
Type=forking
User=mongodb
PermissionsStartOnly=true
EnvironmentFile=/etc/sysconfig/mongod-arbiter
ExecStartPre=-/usr/bin/mkdir /var/run/mongodb-arbiter
ExecStartPre=/usr/bin/chown -R mongodb:root /var/run/mongodb-arbiter
ExecStart=/usr/bin/mongod $OPTIONS run
ExecStopPost=-/usr/bin/rm -rf /var/run/mongodb-arbiter
PrivateTmp=true
LimitNOFILE=64000
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
```

Create paths for arbiter:

```
mkdir /var/lib/mongodb-arbiter
chown mongodb:root /var/lib/mongodb-arbiter
chmod 750 /var/lib/mongodb-arbiter
```

Start the arbiter service:

```
systemctl start mongodb-arbiter
```

Once arbiter is live, you need to add it to MongoDB's replicaset. Connect to mongo shell with root priviledges:

```
mongo -u root -p <password> --authenticationDatabase admin
```

Add arbiter to replica's config:

```
rs.addArb("10.30.255.254:27018")
```

Check status:
```
luna:PRIMARY> rs.status()
```

At this point you are ready to copy data and configuration to the other node.

Shutdown the arbiter on the first node:

```
systemctl stop mongod-arbiter
```

Copy the configuration files:

```
for f in /etc/mongod-arbiter.conf /etc/sysconfig/mongod-arbiter /etc/systemd/system/mongod-arbiter.service /var/lib/mongodb-arbiter; do scp -pr $f master2:$f ; done
```

On the second node fix ownership and permissions:

```
chown -R mongodb:root /var/lib/mongodb-arbiter
chmod 750 /var/lib/mongodb-arbiter
```

Bring floating ip down on first node:

```
ip a del 10.30.255.254/16 dev eth1
```
And bring it up on second

```
ip a add 10.30.255.254/16 dev eth1
```

Run the arbiter on the second node

```
systemctl start mongod-arbiter
```

Connect to mongo shell and make sure that you have all instances up:

```
luna:PRIMARY> rs.status()
```
