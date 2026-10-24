"""A tiny SMTP server for the smoke test: accepts any message and prints it to the log.

Only for local testing. It speaks just enough SMTP for Python's smtplib and does no TLS.
"""

import socketserver


class Handler(socketserver.StreamRequestHandler):
    def reply(self, text: str) -> None:
        self.wfile.write((text + "\r\n").encode())

    def handle(self) -> None:
        self.reply("220 sink ready")
        data_mode, lines = False, []
        for raw in self.rfile:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if data_mode:
                if line == ".":
                    data_mode = False
                    print("=== MAIL BEGIN ===\n" + "\n".join(lines) + "\n=== MAIL END ===", flush=True)
                    lines = []
                    self.reply("250 queued")
                else:
                    lines.append(line[1:] if line.startswith("..") else line)
                continue
            command = line.split(" ", 1)[0].upper()
            if command in ("EHLO", "HELO"):
                self.reply("250 sink")
            elif command in ("MAIL", "RCPT", "RSET", "NOOP"):
                self.reply("250 ok")
            elif command == "DATA":
                data_mode = True
                self.reply("354 go ahead")
            elif command == "QUIT":
                self.reply("221 bye")
                return
            else:
                self.reply("502 not implemented")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    with Server(("0.0.0.0", 2525), Handler) as server:
        print("smtp sink listening on 2525", flush=True)
        server.serve_forever()
