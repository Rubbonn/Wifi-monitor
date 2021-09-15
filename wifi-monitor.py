# TODO Possibilità di specificare mac e canale tra le opzioni
# TODO Intercettare SIGINT per annullare le operazioni e reimpostare la scheda di rete
import subprocess, sys, getopt, time, re


# Definizione funzioni
def shutdownNm(interfaccia):
	subprocess.run(["nmcli", "device", "set", interfaccia, "managed", "no"], check=True)

def startNm(interfaccia):
	subprocess.run(["nmcli", "device", "set", interfaccia, "managed", "yes"], check=True)

def monitorMode(interfaccia):
	subprocess.run(["ifconfig", interfaccia, "down"], check=True)
	subprocess.run(["iwconfig", interfaccia, "mode", "Monitor"], check=True)
	subprocess.run(["ifconfig", interfaccia, "up"], check=True)

def managedMode(interfaccia):
	subprocess.run(["ifconfig", interfaccia, "down"], check=True)
	subprocess.run(["iwconfig", interfaccia, "mode", "Managed"], check=True)
	subprocess.run(["ifconfig", interfaccia, "up"], check=True)

def restore(interfaccia):
	managedMode(interfaccia)
	startNm(interfaccia)

def getWifiInfo(essid=None):
	cellNumberRe = re.compile(r"-\s+Address:\s(?P<mac>.+)$")
	regexps = [
	    re.compile(r"^ESSID:\"(?P<essid>.*)\"$"),
	    re.compile(r"\(Channel (?P<channel>\d+)\)$"),
	    re.compile(r"Encryption key:(?P<encryption>.+)$"),
	]
	try:
		output = subprocess.check_output(["iwlist", interfaccia, "scan"], text=True)
	except:
		print("C'è stato un problema nella scansione")
		return False
	reti = []
	for linea in output.splitlines():
		linea = linea.strip()
		cellNumber = cellNumberRe.search(linea)
		if(cellNumber is not None):
			reti.append(cellNumber.groupdict())
			continue
		for expression in regexps:
			result = expression.search(linea)
			if(result is not None):
				reti[-1].update(result.groupdict())
				continue
	if(essid != None):
		for rete in reti:
			if(rete["essid"] == essid):
				return rete
		return False
	else:
		return reti



# Inizio programma
try:
	parametri, argomenti = getopt.getopt(sys.argv[1:], "hi:t:a:")
except getopt.GetoptError:
	print("Parametri non validi")
	print(f"Uso: sudo python3 {sys.argv[0]} -h -i <interfaccia> -t <tempo di cattura in secondi> [-a <nome della rete>]")
	print("-a\t Se omesso verrà effettuata una scansione delle reti circostanti e potrai scegliere quale monitorare")
	sys.exit(2)
interfaccia = tempo = rete = None
for parametro, valore in parametri:
	if(parametro == "-h"):
		print(f"Uso: sudo python3 {sys.argv[0]} -i <interfaccia> -t <tempo di cattura in secondi> [-a <nome della rete>]")
		print("-a\t Se omesso verrà effettuata una scansione delle reti circostanti e potrai scegliere quale monitorare")
		sys.exit(0)
	if(parametro == "-i"):
		interfaccia = valore
	elif(parametro == "-t"):
		try:
			tempo = int(valore)
		except ValueError:
			print("Tempo non valido")
			sys.exit(2)
	elif(parametro == "-a"):
		rete = valore
if(interfaccia == None or tempo == None):
	print("Mancano dei parametri obbligatori")
	sys.exit(2)
if(rete == None):
	print("Scansione delle reti circostanti...")
	reti = getWifiInfo()
	reti = list(filter(lambda rete: len(rete["essid"]) > 0, reti))
	if(len(reti) == 0):
		print("Non sono state trovate reti")
		sys.exit(0)
	for i in range(len(reti)):
		print(f"{i}) Essid: {reti[i]['essid']} - Mac: {reti[i]['mac']} - Canale: {reti[i]['channel']} - Protezione: {reti[i]['encryption']}")
	while True:
		try:
			rete = int(input("Quale rete vuoi monitorare? "))
			if(rete >= len(reti) or rete < 0):
				print("Inserisci un numero entro le opzioni")
				continue
			break
		except:
			print("Inserisci un numero valido")
	rete = reti[rete]
else:
	print("Ricerca della rete in corso...")
	rete = getWifiInfo(rete)
	if(not rete):
		print("La rete specificata non è stata trovata")
		sys.exit(1)
	print(f"Rete trovata, mac: {rete['mac']}, canale: {rete['channel']}")
try:
	print("Escludo l'interfaccia dal Network Manager")
	shutdownNm(interfaccia)
	print("Interfaccia esclusa, imposto la scheda in modalità monitor")
	monitorMode(interfaccia)
except:
	print("C'è stato un errore")
	restore(interfaccia)
	sys.exit(1)
print("Scheda impostata, inizio monitoraggio")
airodump = subprocess.Popen(["airodump-ng", "-w", "hack_wifi", "--output-format", "pcap", "-d", rete["mac"], "-c", rete["channel"], interfaccia], stdout=None)
time.sleep(tempo)
terminato = False
airodump.terminate()
while(not terminato):
	try:
		airodump.wait(30)
		terminato = True
	except:
		print("Airodump non risponde, chiusura forzata")
		airodump.kill()
print("Fine monitoraggio, ripristino la connessione")
restore(interfaccia)
sys.exit(0)
