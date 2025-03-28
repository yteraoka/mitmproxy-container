# mitmproxy-container

https://mitmproxy.org/ を使って HTTP Request を JSON で stdout に出力する

```
docker run --rm -p 8080 -t ghcr.io/yteraoka/mitmproxy-container
```

```
curl -skx http://127.0.0.1:8080 https://www.example.com/
```

mitmproxy (mitmdump) は初回起動時に CA 証明書(+秘密鍵)を `~/.mitmproxy` ディレクトリに作成するが
事前に作成したものを使うことも可能

```
openssl req -x509 -new \
  -nodes -newkey rsa:2048 -keyout ca.key \
  -sha256 -out ca.crt -days 3650 \
  -addext keyUsage=critical,keyCertSign,cRLSign \
  -addext extendedKeyUsage=serverAuth \
  -subj /CN=mitmproxy/O=mitmproxy
```

```
cat ca.key ca.crt > ~/.mitmproxy/mitmproxy-ca.pem
```

この Dockerfile では環境変数 `MITMPROXY_CACERT_WITH_KEY` の中身を `~/.mitmproxy/mitmproxy-ca.pem` に書き出すようになっているため

```
docker run --rm -p 8080 -t \
  -e MITMPROXY_CACERT_WITH_KEY="$(cat ~/.mitmproxy/mitmproxy-ca.pem)" \
  ghcr.io/yteraoka/mitmproxy-container
```

として

```
curl -sx http://127.0.0.1:8080 --cacert ca.crt https://www.example.com/
```

mitmproxy の発行する証明書を信頼することができる
