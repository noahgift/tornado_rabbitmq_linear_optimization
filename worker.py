import pika
from coopr.pyomo import (ConcreteModel, Objective, Var, NonNegativeReals,
                              maximize, Constraint)
from coopr.opt import SolverFactory
import time

def do_pyomo_work(profit_rate_windows):
    
    Products = ['Doors', 'Windows']
    ProfitRate = {'Doors':300, 'Windows':profit_rate_windows}
    Plants = ['Door Fab', 'Window Fab', 'Assembly']
    HoursAvailable = {'Door Fab':4, 'Window Fab':12, 'Assembly':18}
    HoursPerUnit = {('Doors','Door Fab'):1, ('Windows', 'Window Fab'):2,
                    ('Doors','Assembly'):3, ('Windows', 'Assembly'):2,
                    ('Windows', 'Door Fab'):0, ('Doors', 'Window Fab'):0}
    
    #Concrete Model
    model = ConcreteModel()
    #Decision Variables
    model.WeeklyProd = Var(Products, within=NonNegativeReals)
    
    #Objective
    model.obj = Objective(expr=
                sum(ProfitRate[i] * model.WeeklyProd[i] for i in Products),
                sense = maximize)
    
    def CapacityRule(model, p):
        """User Defined Capacity Rule
        
        Accepts a pyomo Concrete Model as the first positional argument,
        and a list of Plants as a second positional argument
        """
        
        return sum(HoursPerUnit[i,p] * model.WeeklyProd[i] for i in Products) <= HoursAvailable[p]

    model.Capacity = Constraint(Plants, rule = CapacityRule)
    opt = SolverFactory("glpk")
    instance = model.create()
    results = opt.solve(instance)
    #results.write()
    return results.Solution()

def create_channel():
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
    channel.queue_declare(queue="pyomo-queue") 
    channel.queue_bind(queue="pyomo-queue",     
                   exchange="pyomo-job-exchange",
                   routing_key="pyomo-job-dispatch")
    return channel

def consume_run_loop():
    channel = create_channel()
    def msg_consumer(channel, method, header, body):
        channel.basic_ack(delivery_tag=method.delivery_tag) 
        print body
        now = time.time()
        res = do_pyomo_work(int(body))
        print res
        print "Pyomo Job Completed in: %s seconds" % round(time.time() - now, 2)
        return
    channel.basic_consume( msg_consumer, 
                           queue="pyomo-queue",
                           consumer_tag="pyomo-consumer")
    channel.start_consuming()

consume_run_loop()