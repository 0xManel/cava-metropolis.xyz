import http.server
import socketserver
import webbrowser
import socket

PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

# Permite reusar a porta caso você reinicie o servidor rapidamente
class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Tenta conectar a um IP externo para descobrir o IP local (não envia dados reais)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

print(f"🚀 Cava Metropolis rodando!\n💻 No PC: http://localhost:{PORT}\n📱 No Wi-Fi: http://{get_ip()}:{PORT}")

# Abre o navegador automaticamente
webbrowser.open(f"http://localhost:{PORT}")

with ReusableTCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()