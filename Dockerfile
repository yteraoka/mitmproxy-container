FROM public.ecr.aws/docker/library/debian:12.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends pipx \
 && groupadd -g 2000 mitmproxy \
 && useradd -m -u 2000 -g mitmproxy mitmproxy

COPY --chmod=0755 docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 8080

USER mitmproxy

WORKDIR /home/mitmproxy

RUN pipx install mitmproxy \
 && pipx inject mitmproxy requests

COPY jsondump.py .

CMD ["/docker-entrypoint.sh"]
