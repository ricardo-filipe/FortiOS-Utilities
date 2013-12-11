#!/usr/bin/env python

import sys
import re
from struct import unpack
from socket import inet_aton, gethostbyname
from ordereddict import OrderedDict
from datetime import datetime

class fgPolicy(object):
	"""Class for a FortiOS Policy"""
	def __init__(self,id=None):
		if id == None:
				raise ValueError,"missing policy information"

		self.id = id
		self.src_zone = ""
		self.dst_zone = ""

		self.webauth = False
		self.traffic = False
		self.log = False
		self.schedule = False
		self.attack = False
		self.nat = ""

		self.action = ""

		self.disabled = False

		self.src_addr = []
		self.dst_addr = []
		self.svc = []

	def set_srcintf(self,src):
		self.src_zone = src.replace('"','')

	def set_dstintf(self,dst):
		self.dst_zone = dst.replace('"','')
	
	def set_nat(self,type):
		self.nat = type.capitalize()

	def set_action(self,action):
		self.action = action.capitalize()

	def add_svc(self,service):
		self.svc.append(service.replace('"',''))

	def add_src(self,addr):
		self.src_addr.append(addr.replace('"',''))

	def add_dst(self,addr):
		self.dst_addr.append(addr.replace('"',''))

	def set_traffic(self):
		self.traffic = True

	def set_log(self):
		self.log = True
	
	def set_webauth(self):
		self.webauth = True
	
	def set_disable(self):
		self.disabled = True

	def set_attack(self):
		self.attack = True

	def set_schedule(self):
		self.schedule = True

def print_policy(policies=[]):

	print "[1;34m%5s %-15s %-15s %-25s %-25s %-15s %-15s %-10s %-4s %s[m" % ("ID","From","To","Src-address","Dst-address","Service","Action","State","ASTL","NAT")
	for p in policies:
		print "%5s %-15s %-15s %-25s %-25s %-15s %-15s %-18s %s%s%s%s %s" % (p.id,p.src_zone[0:15],p.dst_zone[0:15],p.src_addr[0][0:25],p.dst_addr[0][0:25],p.svc[0][0:15],p.action,"[31mdisabled[m" if p.disabled else "[32menabled[m","X" if p.attack else "-","X" if p.schedule else "-","X" if p.traffic else "-","X" if p.log else "-",p.nat)
		
		array_max = max(len(p.src_addr),len(p.dst_addr),len(p.svc))
		if len(p.src_addr) < array_max:
			p.src_addr += [''] * (array_max - len(p.src_addr))
		if len(p.dst_addr) < array_max:
			p.dst_addr += [''] * (array_max - len(p.dst_addr))
		if len(p.svc) < array_max:
			p.svc += [''] * (array_max - len(p.svc))

		for i in range(1,array_max):
			print "%37s %-25s %-25s %-15s" % ('',p.src_addr[i][0:25],p.dst_addr[i][0:25],p.svc[i])

if __name__ == '__main__':

	if not len(sys.argv) >= 4:
		sys.stderr.write("Usage: %s <fg config> <vdom> [ <policy id> | <from zone> <to zone> ]\n" % sys.argv[0])
		sys.exit(1)

	config = []
	policy_dict = OrderedDict()

	vdom = sys.argv[2]

	in_vdom = 0
	in_policy = False

	sys.stdout.write("Loading configuration...")
	
	try:
		fd = open(sys.argv[1],'r')
		for line in fd.readlines():
			if line[:-1] == "edit "+vdom:
				in_vdom += 1

			#if line[:-1] == "config firewall policy6" and in_vdom == 2: # for v6 policies
			if line[:-1] == "config firewall policy" and in_vdom == 2: # for vdom config, first 'edit <vdom>' is blank config
				in_policy = True

			if line[:-1] == "end" and in_policy:
				config.append(line.strip())
				break

			if in_policy: 
				config.append(line.strip())

		fd.close()
		config.pop() # pop "end" off
	except:
		sys.stderr.write("\nFATAL: unable to open file %s\n" % sys.argv[1] )
		sys.exit(1)

	config_iter = iter(config)

	in_policy = False

	for line in config_iter:

		if line == "end":
			# skip sub policy blocks
			continue

		if line == "next":
			policy_dict[policy.id] = policy
			in_policy = False
			continue

		[cmd,args] = line.split(None,1)

		if cmd == "edit" and in_policy:
			# skip sub policy blocks
			continue

		if cmd == "edit":
			in_policy = True;
			policy = fgPolicy(args)
			if policy_dict.has_key(policy.id):
				sys.stderr.write("Duplicate policy id entry detected: %s\n" % policy.id)
			continue

		if cmd == "set":

			[option,opt_args] = args.split(None,1)

			if option == "srcintf":
				policy.set_srcintf(opt_args)
			elif option == "dstintf":
				policy.set_dstintf(opt_args)
			elif option == "srcaddr":
				for addr in opt_args.split():
					policy.add_src(addr)
			elif option == "dstaddr":
				for addr in opt_args.split():
					policy.add_dst(addr)
			elif option == "service":
				for svc in opt_args.split():
					policy.add_svc(svc)
			elif option == "action":
				policy.set_action(opt_args)
			elif option == "nat":
				policy.set_nat('S')
			elif option == "ippool":
				policy.set_nat('D')
			elif option == "identity-based":
				policy.set_webauth()
				policy.set_action(policy.action + "~")
			elif option == "schedule":
				if opt_args != '"always"':
					policy.set_schedule()
			elif option == "utm-status":
				if opt_args == "enable":
					policy.set_attack()
			elif option == "per-ip-shaper" or option == "traffic-shaper":
				policy.set_traffic()
			elif option == "logtraffic":
				if opt_args == "all":
					policy.set_log()
			elif option == "status":
				if opt_args == "disable":
					policy.set_disable()

	sys.stdout.write("complete. %s policies loaded.\n" % len(policy_dict))

	if sys.argv[3].isdigit():	
		print_policy([policy_dict[sys.argv[3]],])

	if len(sys.argv) == 5:
		policies = []
		for policy in policy_dict:
			if policy_dict[policy].src_zone.lower() == sys.argv[3].lower() and policy_dict[policy].dst_zone.lower() == sys.argv[4].lower():
				policies.append(policy_dict[policy])

		print_policy(policies)

# vim: ts=4 sw=4 nowrap