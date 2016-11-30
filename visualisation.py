import Tkinter as tk
import multiprocessing
import dill
import time

_process = None

def visualize(grid):
	def runner(q):
		gui = _GUI(q, master = tk.Tk())
		gui.master.title('Drones')
		gui.mainloop() 

	global _process

	if _process is None or not _process.isAlive():
		_process = _Process(runner)

	_process.send(grid)
	time.sleep(0.1) # TODO: hacky?

class _Process(object):
	def __init__(self, runner):
		self._queue = multiprocessing.Queue()
		self._process = multiprocessing.Process(target=runner, name="visualizer", args=(self._queue,)) 
		self._process.start()

	def send(self, message):
		self._queue.put(message)

	def isAlive(self):
		return self._process.is_alive()

class _GUI(tk.Frame):
	def __init__(self, queue, master = None):
		tk.Frame.__init__(self, master)
		self.grid()
		self.queue = queue
		self.after(100, self._poll)
		self.cellSize = 50
		self.field = None

	def _poll(self):
		if not self.queue.empty():
			self._draw()
		self.after(1000, self._poll)

	def _draw(self):
		if self.field:
			self.field.grid_forget()

		grid = self.queue.get()
		self.field = tk.Canvas(self, width = grid.width * self.cellSize, height = grid.height * self.cellSize)
		for pos in grid:
			self.field.create_rectangle(
				pos.x * self.cellSize, pos.y * self.cellSize,
				pos.x * self.cellSize + self.cellSize, pos.y * self.cellSize + self.cellSize,
				outline="#000000")

			if grid.warehousesAt(pos):
				self._drawWarehouseAt(grid.warehousesAt(pos)[0], pos)

			if grid.customersAt(pos):
				self._drawCustomerAt(grid.customersAt(pos)[0], pos)

			if grid.dronesAt(pos):
				self._drawDroneAt(grid.dronesAt(pos)[0], pos)

		self.field.grid()

	def _drawWarehouseAt(self, warehouse, pos):
		size = self.cellSize / 2
		x, y = pos.x * self.cellSize, pos.y * self.cellSize
		self.field.create_oval(
				x, y,
				pos.x * self.cellSize + size, pos.y * self.cellSize + size,
				outline="#00FF00"
		)
		self.field.create_text(
				(x + size / 2, y + size / 2),
				text=warehouse.name[0].upper()
		)

	def _drawCustomerAt(self, customer, pos):
		size = self.cellSize / 2
		x, y = pos.x * self.cellSize + size, pos.y * self.cellSize
		self.field.create_oval(
				x, y,
				pos.x * self.cellSize + 2 * size, pos.y * self.cellSize + size,
				outline="#0000FF"
		)
		self.field.create_text(
				(x + size / 2, y + size / 2),
				text=customer.name[0].upper()
		)

	def _drawDroneAt(self, drone, pos):
		size = self.cellSize / 2
		x, y = pos.x * self.cellSize, pos.y * self.cellSize + size
		self.field.create_oval(
				x, y,
				pos.x * self.cellSize + size, pos.y * self.cellSize + 2 * size,
				outline="#FF0000"
		)
		self.field.create_text(
				(x + size / 2, y + size / 2),
				text=drone.name[0].upper()
		)

	