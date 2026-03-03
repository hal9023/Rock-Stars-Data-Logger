dataFile = open("Example Data Sets\PRESSURE.TXT")
data = dataFile.read()
logRate = 5 # times per second


def processData(data):
    data = data.splitlines()

    return data

text = processData(data)


def getTime(t): 
    time = len(t) / logRate

    return time

runTime = getTime(text)
print(str(runTime) + " Seconds")