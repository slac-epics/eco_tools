
def parseGitModulesTxt():
    '''Parse the GIT modules txt file and return a dict of packageName -> location'''
    if not os.path.isfile( gitModulesTxtFile ):
        return {}
    package2Location = {}
    with open(gitModulesTxtFile, 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        parts = line.split()
        if(len(parts) < 2):
            print "Error parsing ", gitModulesTxtFile, "Cannot break", line, "into columns with enough fields using spaces/tabs"
            continue
        packageName = parts[0]
        packageLocation = parts[1]
        package2Location[packageName] = packageLocation
    return package2Location

