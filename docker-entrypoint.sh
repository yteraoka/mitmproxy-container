#!/bin/sh

if [ -n "${MITMPROXY_CACERT_WITH_KEY}" ] ; then
  mkdir $HOME/.mitmproxy
  echo "${MITMPROXY_CACERT_WITH_KEY}" > $HOME/.mitmproxy/mitmproxy-ca.pem
fi

exec $HOME/.local/bin/mitmdump -q -s jsondump.py --set stream_large_bodies=1
