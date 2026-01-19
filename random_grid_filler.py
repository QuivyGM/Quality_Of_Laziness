import random

rows, cols = 4, 7
filled_count = 3        # <<< SET HOW MANY CELLS TO FILL
choices = ["/", "\\"]    # either slash or backslash

# --- generate grid ---
total_cells = rows * cols

# choose which positions will be filled
filled_positions = set(random.sample(range(total_cells), filled_count))

grid = []
for i in range(total_cells):
    if i in filled_positions:
        grid.append(random.choice(choices))
    else:
        grid.append(" ")

# convert flat list → rows
grid = [grid[i*cols:(i+1)*cols] for i in range(rows)]

# --- box-drawn printing ---
top    = "┌" + "───┬" * (cols-1) + "───┐"
middle = "├" + "───┼" * (cols-1) + "───┤"
bottom = "└" + "───┴" * (cols-1) + "───┘"

print(top)
for r in range(rows):
    print("│ " + " │ ".join(grid[r]) + " │")
    if r < rows-1:
        print(middle)
print(bottom)
