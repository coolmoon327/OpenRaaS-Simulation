import numpy

class test(object):
    def __init__(self,a) -> None:
        self.a = a
    
l = []    
for i in range(10):
    t = test(i*10)
    l.append(t)
ll = []

for x in l:
    if x.a < 50:
        ll.append(x)

for x in ll:
    l.remove(x)

for x in l:
    print(x.a)