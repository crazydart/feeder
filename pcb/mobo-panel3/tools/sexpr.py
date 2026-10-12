import re,json
class Atom(str): pass
def parse(s):
 stack=[]; roots=[]
 for t in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+',s):
  if t=='(':
   n=[]
   if stack: stack[-1].append(n)
   else: roots.append(n)
   stack.append(n)
  elif t==')': stack.pop()
  else:
   if t.startswith('"'):
    try:t=json.loads(t)
    except:t=t[1:-1]
   else:t=Atom(t)
   stack[-1].append(t)
 return roots[0]
def ch(n,k): return [x for x in n if isinstance(x,list) and x and x[0]==k]
def one(n,k): return next((x for x in n if isinstance(x,list) and x and x[0]==k),None)
def val(n,k):
 x=one(n,k); return x[1] if x and len(x)>1 else None
def emit(n,depth=0):
 if isinstance(n,list):
  if all(not isinstance(x,list) for x in n): return '('+' '.join(emit(x) for x in n)+')'
  s='('; first=True
  for x in n:
   if isinstance(x,list):s+='\n'+'  '*(depth+1)+emit(x,depth+1)
   else:s+=('' if first else ' ')+emit(x)
   first=False
  return s+'\n'+'  '*depth+')'
 if isinstance(n,Atom):return str(n)
 if isinstance(n,(int,float)):return str(n)
 return json.dumps(n,ensure_ascii=False)
