"""Refill the copper pours with KiCad's own zone filler."""
import sys, pcbnew
path = sys.argv[1]
board = pcbnew.LoadBoard(path)
filler = pcbnew.ZONE_FILLER(board)
zones = board.Zones()
ok = filler.Fill(zones)
pcbnew.SaveBoard(path, board)
print(f'filled {len(zones)} zones, filler returned {ok}')
