import https from "node:https";

export default function handler(req, res) {
  const HOST = process.env.UPSTREAM_HOST;

  if (!HOST || !/^[a-z0-9.-]+$/i.test(HOST)) {
    return res.status(503).send("UPSTREAM_HOST no configurado");
  }

  if (!["GET", "HEAD"].includes(req.method)) {
    res.setHeader("Allow", "GET, HEAD");
    return res.status(405).send("Method Not Allowed");
  }

  const url = new URL(req.url, "https://localhost");
  const route = url.searchParams.get("__route") || "";

  url.searchParams.delete("__route");

  const upstream = https.request(
    {
      hostname: HOST,
      servername: HOST,
      port: 443,
      method: req.method,
      path: "/" + route.replace(/^\/+/, "") + url.search,
      headers: {
        Host: HOST,
        Accept: req.headers.accept || "*/*"
      },
      timeout: 15000
    },
    (response) => {
      res.statusCode = response.statusCode || 502;

      for (const header of [
        "content-type",
        "content-length",
        "content-encoding",
        "location"
      ]) {
        if (response.headers[header] !== undefined) {
          res.setHeader(header, response.headers[header]);
        }
      }

      res.setHeader("Cache-Control", "no-store");
      response.pipe(res);
    }
  );

  upstream.on("timeout", () => {
    upstream.destroy(new Error("Timeout"));
  });

  upstream.on("error", (error) => {
    console.error("Upstream error:", error.message);

    if (!res.headersSent) {
      res.statusCode = 502;
      res.end("Upstream unavailable");
    } else {
      res.destroy();
    }
  });

  upstream.end();
}