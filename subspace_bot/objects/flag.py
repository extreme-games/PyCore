class Flag():

    def __init__(self, flag_id, pid=0xFFFF, freq=0xFFFF, x=0xFFFF, y=0xFFFF):
        self.id = flag_id
        self.freq = freq  # if == FREQ_NONE flag neuted
        self.x = x  # if == coord_none  flag is carried
        self.y = y  # if == coord_none  flag is carried
