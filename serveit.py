import logging
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from get_pass import Passer
from errors import *
import urllib3.util
from utils import *
from dotenv import load_dotenv

load_dotenv()

HEADLESS = True
hostName = '0.0.0.0'
port = int(os.environ.get('PORT'))


class HttpRequestHandler(BaseHTTPRequestHandler):
    busying = False
    code = 200
    message = ''
    content = b''

    def get_pass_image(self, net_id, net_pw, duo_code):
        try:
            HttpRequestHandler.busying = True
            passer = Passer(net_id, net_pw, duo_code,headless=HEADLESS)
            self.code = 200
            self.content = passer.get_pass_and_reminder().encode()
        except IncorrectPasswordError as e:
            logging.error(e.message + ' for ' + e.net_id)
            self.message = "Your given password may be wrong, we cannot do Trojan Check for you."
            self.code = 400
        except DuoCodeError as e:
            self.message = e.message
            self.code = 400
        except SelfAssessmentNotCompliantError as e:
            logging.error(e.message)
            self.message = "We failed to do wellness assessment for you.\n\n" + e.notification
            self.code = 400
        except UnexpectedUrlError as e:
            logging.error(f"Unexpected url: {e.url}. Unable to save pass. Exit.")
            logging.error(f"Screenshot saved as {e.image_name}")
            self.message = "Internal error, maybe due to the website updates. You can report the issue to us."
            self.code = 500
        finally:
            HttpRequestHandler.busying = False

    def do_GET(self):
        if HttpRequestHandler.busying:
            self.code = 503
            self.message = 'Server is busying'
        else:
            parsed_url: urllib3.util.Url = urllib3.util.parse_url(self.path)
            if parsed_url.path == '/trojan-pass':
                try:
                    qs = urllib.parse.parse_qs(parsed_url.query)
                    net_id = qs['id'][0]
                    net_pw = qs['pw'][0]
                    duo_code = qs['code'][0]
                    self.get_pass_image(net_id, net_pw, duo_code)
                except IndexError:
                    self.code = 400
                    self.message = 'Invalid arguments'
            else:
                self.code = 404

        self.send_response(self.code)
        self.end_headers()
        if self.message:
            self.wfile.write(f"<p>{self.message}</p>\n".encode())
            return
        if self.content:
            self.wfile.write(self.content)


if __name__ == '__main__':
    webServer = HTTPServer((hostName, port), HttpRequestHandler)

    try:
        logging.debug(f'Server will start at ${hostName}:${port}')
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        webServer.server_close()
        logging.info('Server closed.')
