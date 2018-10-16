class Building():
    def __init__(self, gid, x, y, z):
        self.gid = gid
        self. x = x
        self.y = y
        self.z = z

    def __init__(self, tup):
        self.gid = tup[0]
        self.x = tup[2]
        self.y = tup[3]
        self.z = tup[1]

    def __str__(self):
        return "Building ID: {0} \nLongitude: {1} \nLatitude: {2} \nHeigth of the roof: {3}".format(self.gid, self.x, self.y, self.z)
