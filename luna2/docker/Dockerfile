FROM docker.io/centos:7.5.1804
RUN yum install -y epel-release ipmitool
RUN yum install -y https://repo.mongodb.org/yum/redhat/7/mongodb-org/4.0/x86_64/RPMS/mongodb-org-server-4.0.4-1.el7.x86_64.rpm
RUN yum install -y https://repo.mongodb.org/yum/redhat/7/mongodb-org/4.0/x86_64/RPMS/mongodb-org-shell-4.0.4-1.el7.x86_64.rpm
RUN yum install -y https://repo.mongodb.org/yum/redhat/7/mongodb-org/4.0/x86_64/RPMS/mongodb-org-tools-4.0.4-1.el7.x86_64.rpm
RUN yum install -y https://github.com/rabbitmq/erlang-rpm/releases/download/v21.1.2/erlang-21.1.2-1.el7.centos.x86_64.rpm
RUN yum install -y https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.7.9/rabbitmq-server-3.7.9-1.el7.noarch.rpm
RUN yum install -y python2-pip
RUN pip2 install supervisor
RUN yum install -y python36 python36-setuptools
RUN python36 -mvenv env
RUN env/bin/pip install pip --upgrade
COPY conf/env/requirements.txt /tmp/requirements.txt
RUN env/bin/pip install -r /tmp/requirements.txt
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN useradd -r luna
COPY conf/supervisor/supervisord.conf /etc/supervisord.conf
ENTRYPOINT ["/entrypoint.sh"]
