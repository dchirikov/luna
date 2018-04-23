# How to enable HTTPS support in luna

Strictly speaking HTTPS support is being provided by frontend server. Luna just needs to be aware about it:

```
luna cluster change --frontend_https yes
```

Assume we have nginx as frontend server.

### Configuring `nginx`

1. Create directories
    ```
    mkdir /etc/ssl/private
    chmod 700 /etc/ssl/private

    cd /etc/ssl/private/
    ```

2. Issue CA certificate
    ```
    openssl genrsa -des3 -out ca.key 4096
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -key /etc/ssl/private/ca.key -out /etc/ssl/certs/ca.crt
    ```

3. Add newly created cert to system bundle, we dont want to use `curl -k`
    ```
    cat /etc/ssl/certs/ca.crt >> /etc/ssl/certs/ca-bundle.crt
    ```

4. Create certificate request for nginx and sign it with CA certificate
    ```
    mkdir -p /etc/ssl/nginx/{private,certs}
    cd /etc/ssl/nginx/private
    ```

5. Create server private key
    ```
    # please note this key is not encrypted.
    openssl genrsa -out nginx.key.insecure 4096
    ```

6. Create cert request
    ```
    # you need to specify IP address of the server here, not hostname
    openssl req -new -key nginx.key.insecure -out nginx.csr
    ```

7. Sign request
    ```
    openssl x509 -req -days 365  -CA /etc/ssl/certs/ca.crt -CAkey /etc/ssl/private/ca.key -set_serial 01  -in /etc/ssl/nginx/private/nginx.csr -out /etc/ssl/nginx/certs/nginx.crt
    ```

8. Nginx requires Diffie Hellman parameters to be generated
    ```
    openssl dhparam -out /etc/ssl/nginx/certs/nginx.dhparam.pem 2048
    ```
9. Edit `/etc/nginx/conf.d/luna.conf`
    ```
    mv /etc/nginx/conf.d/luna.conf{,.bkp}
    # diff /etc/nginx/conf.d/{luna.conf.bkp,luna-secured.conf}
    7c7,11
    <     listen 7050;
    ---
    >     listen 7050 http2 ssl;
    >     server_name 10.61.255.254;
    >     ssl_certificate /etc/ssl/nginx/certs/nginx.crt;
    >     ssl_certificate_key /etc/ssl/nginx/private/nginx.key.insecure
    ```
Now nginx is ready to handle HTTPS requests. Other https options can be taken from [here](https://cipherli.st/) and [here](https://raymii.org/s/tutorials/Strong_SSL_Security_On_nginx.html)

### Configuring iPXE

By default iPXE does not support https as a boot source. We need to re-compile binary from source.
```
git clone git://git.ipxe.org/ipxe.git
cd ipxe/src
sed -i -e 's/#undef\(\WDOWNLOAD_PROTO_HTTPS.*\)/#define\1/' ./config/general.h
make bin/undionly.kpxe TRUST=/etc/ssl/certs/ca.crt CERT=/etc/ssl/certs/ca.crt
cp bin/undionly.kpxe /tftpboot/luna_undionly.kpxe
```
Please note the we are compilig undionly.kpxe binary here which is being downloaede by node on boot. It will work for those network cards which are using PXE. Some vendors are flashing adapters with iPXE on factory so procedure might differ for them.

Another binary needs to be compiled if virtual machines if they need to be booted by Luna. Hypervisors are supplied with iPXE binaries and do not download them from tftp server. For instance quemu-kvm is storing roms in /usr/share/ipxe. So they need to be replaced with custom binaries.

```
make bin/10ec8139.rom TRUST=/etc/ssl/certs/ca.crt CERT=/etc/ssl/certs/ca.crt
```

