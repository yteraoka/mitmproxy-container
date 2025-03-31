#!/bin/sh

if [ -n "${MITMPROXY_CACERT_WITH_KEY}" ] ; then
  mkdir $HOME/.mitmproxy
  echo "${MITMPROXY_CACERT_WITH_KEY}" > $HOME/.mitmproxy/mitmproxy-ca.pem
fi

UPSTREAM_CACERT_OPT=""
if [ -n "${UPSTREAM_CACERT}" ] ; then
  echo "${UPSTREAM_CACERT}" > upstream_cacert.pem
  UPSTREAM_CACERT_OPT="--set ssl_verify_upstream_trusted_ca=$HOME/upstream_cacert.pem"
fi

exec $HOME/.local/bin/mitmdump -q -s jsondump.py --set stream_large_bodies=1 $UPSTREAM_CACERT_OPT
