#!/bin/bash
# Recipe for app-hello: a tiny HTTP service on top of app-base, run by systemd.
# scripts/build-image.sh runs this inside a throwaway container, then publishes it.
# $1 is the git ref being built; a real app would clone its source at that ref here.
set -euo pipefail
REF="${1:-main}"

install -d /opt/hello
cat > /opt/hello/server.js <<'JS'
const http = require("http");
const greeting = process.env.GREETING || "hello";
http.createServer((req, res) => {
  if (req.url === "/health") { res.writeHead(200); return res.end("ok\n"); }
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end(greeting + "\n");
}).listen(Number(process.env.PORT || 8080));
JS
echo "$REF" > /opt/hello/VERSION

# Configuration comes from /etc/default/hello (written by native-ops from the manifest's env),
# never from `incus config set environment.*`, which systemd services do not see.
cat > /etc/systemd/system/hello.service <<'UNIT'
[Unit]
Description=hello (native-ops example app)
After=network-online.target

[Service]
EnvironmentFile=-/etc/default/hello
ExecStart=/usr/bin/node /opt/hello/server.js
DynamicUser=yes
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNIT
systemctl enable hello.service
