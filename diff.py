import os

from analysedump import readdump
from galileo import s2a

def LCS(X, Y):
    m = len(X)
    n = len(Y)
    C = [[0] * (n+1) for i in range(m+1)]
    for i in range(1, m+1):
        for j in range(1, n+1):
            if X[i-1] == Y[j-1]:
                C[i][j] = C[i-1][j-1] + 1
            else:
                C[i][j] = max(C[i][j-1], C[i-1][j])
    return C

SYMBOLS = {0: ' ',
           -1: '-',
           1: '+'}

def _diff(C, X, Y, i, j):
    while (i, j) != (0, 0):
        if X[i-1] == Y[j-1]:
            yield (0, X[i-1])
            i -= 1; j -= 1
        elif j > 0 and ((i == 0) or (C[i][j-1] >= C[i-1][j])):
            yield (1, Y[j-1])
            j -= 1
        elif i > 0 and ((j == 0) or C[i][j-1] < C[i-1][j]):
            yield (-1, X[i-1])
            i -= 1
        else:
            assert False

def diff(X, Y, maxL=20):

    start = 0
    oldmode = 0
    s = []
    while start < len(X) and start < len(Y) and X[start] == Y[start]:
        if len(s) == maxL:
            print SYMBOLS[oldmode], ' '.join('%02X' % i for i in s)
            s = []
        s.append(X[start])
        start += 1
    print SYMBOLS[oldmode], ' '.join('%02X' % i for i in s)
    s = []
    X = X[start:]
    Y = Y[start:]

    C = LCS(X, Y)
    for chunk in reversed(list(_diff(C, X, Y, len(X), len(Y)))):
        if s and ((len(s) == maxL) or chunk[0] != oldmode):
            print SYMBOLS[oldmode], ' '.join('%02X' % i for i in s)
            s = []
        s.append(chunk[1])
        oldmode = chunk[0]
    # Print the last one
    print SYMBOLS[oldmode], ' '.join('%02X' % i for i in s)
    return oldmode * len(s)


def dumpdiff(dump1, dump2):
    with open(dump1) as f:
        data1 = readdump(f)

    with open(dump2) as f:
        data2 = readdump(f)

    diff(data1, data2)


def diffdir(basedir):

    for root, dirs, files in os.walk(basedir):
        files = sorted(files)
        for i in range(0, len(files) -1):
            try:
                dumpdiff(os.path.join(root, files[i]), os.path.join(root, files[i+1]))
            except RuntimeError:
                print 'Trouble with %s and %s' % (files[i], files[i+1])
            print '------------------------------------'


if __name__ == "__main__":
    import sys
    diffdir(sys.argv[1])
