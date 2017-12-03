import tornado.ioloop
import tornado.web
import tornado.websocket
import pika
import time

def publish_to_rabbitmq(msg):
    "blocking message sent to RabbitMQ"
    
    credentials = pika.PlainCredentials("guest", "guest")
    conn_params = pika.ConnectionParameters("localhost",
                                            credentials = credentials)
    conn_broker = pika.BlockingConnection(conn_params) 
    channel = conn_broker.channel() 
    channel.exchange_declare(exchange="pyomo-job-exchange", 
                             type="direct",
                             passive=False,
                             durable=False,
                             auto_delete=False)
    
    msg_props = pika.BasicProperties()
    msg_props.content_type = "text/plain"
    channel.basic_publish(body=msg,
                          exchange="pyomo-job-exchange",
                          properties=msg_props,
                          routing_key="pyomo-job-dispatch")

def consume_from_rabbitmq():
    pass

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        msg = "%s" % time.asctime()
        publish_to_rabbitmq(msg)
        self.write(msg)

class PyomoTask(tornado.web.RequestHandler):
    def get(self):
        self.write('<html><body><form action="/pyomo" method="post">'
                   '<input type="text" name="ProfitRateWindows">'
                   '<input type="submit" value="ProfitRateWindows">'
                   '</form></body></html>')

    def post(self):
        self.set_header("Content-Type", "text/plain")
        result = self.get_argument("ProfitRateWindows")
        publish_to_rabbitmq(result)
        self.write("Submitted to RabbitMQ/Pyomo Worker: " + result)
        
class PyomoWebSocketResult(tornado.websocket.WebSocketHandler):

    def open(self):
        """Called when a websocket opens"""
    pass        

application = tornado.web.Application([
    (r"/benchmark", MainHandler),
    (r"/pyomo", PyomoTask),
    (r"/websocket", PyomoWebSocketResult),
    
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
