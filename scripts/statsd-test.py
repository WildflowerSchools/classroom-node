# import statsd
# c = statsd.StatsClient('telegraf.tick.svc.cluster.local', 8125, prefix='wf.test.bucket')
# c.incr('test')
# c.timing('stats.timed', 320)
# c.incr('test')


# c.incr('test')


# c.incr('test')
# c.incr('test')

# pipe = c.pipeline()
# pipe.incr('foo')
# pipe.decr('bar')
# pipe.timing('baz', 520)
# pipe.send()


# echo "a.b.c:1|g" | nc -u statsd.tick.svc.cluster.local 8125

# echo "a.b.c:1|g" | nc -u localhost 8125


echo "wf_measuements,my_tag_key=mytagvalue my_field=\"my field value\"" | nc -u localhost 8092



from telegraf.client import TelegrafClient
client = TelegrafClient(host='telegraf.tick.svc.cluster.local', port=8092)

# Records a three values with different data types
client.metric('wf_tests', {'value': 89, 'used': 6, 'open': 15})

client.metric('wf_tests', {'value': 101, 'used': 36, 'open': 5})

client.metric('wf_tests', {'value': 99, 'used': 16, 'open': 10})

client.metric('wf_tests', {'value': 94, 'used': 26, 'open': 25})



echo "wf_tests,host=myhost,test=true value=2i" | nc -u telegraf.tick.svc.cluster.local 8092


select * from telegraf.autogen.wf_test


SHOW MEASUREMENTS ON "telegraf"
