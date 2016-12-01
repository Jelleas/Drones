import math
import json
import visualisation
import dill
import time
import random

class OutOfStockError(Exception):
	pass

class Position(object):
	def __init__(self, x, y):
		self.x = x
		self.y = y

	def distanceTo(self, pos):
		return math.sqrt((self.x - pos.x)**2 + (self.y - pos.y)**2)

	def __str__(self):
		return "POS [{},{}]".format(self.x, self.y)

	def __repr__(self):
		return str(self)


class Drone(object):
	def __init__(self, name, pos):
		self.name = name
		self._position = pos

	def flyTo(self, pos):
		distance = self.distanceTo(pos)
		self._position = pos
		return distance

	def distanceTo(self, pos):
		return math.ceil(self._position.distanceTo(pos))

	@property
	def position(self):
		return Position(int(round(self._position.x)), int(round(self._position.y)))


class Customer(object):
	def __init__(self, name, pos):
		self.name = name
		self.position = pos

	def __str__(self):
		return "CUSTOMER {}".format(self.name)


class Package(object):
	def __init__(self, name):
		self.name = name

	def __hash__(self):
		return hash(self.name)

	def __eq__(self, other):
		return isinstance(other, type(self)) and other.name == self.name

	def __str__(self):
		return "PACKAGE {}".format(self.name)

	def __repr__(self):
		return str(self)


class Order(object):
	def __init__(self, customer, packages):
		self.customer = customer
		self.packages = packages

	def __str__(self):
		return "ORDER [{} : {}]".format(self.customer, self.packages)

	def __repr__(self):
		return str(self)


class Warehouse(object):
	def __init__(self, name, pos, packages):
		self.name = name
		self.position = pos
		packages = packages
		self._content = {package : packages.count(package) for package in set(packages)}

	def retrieve(self, package):
		try:
			count = self._content[package] - 1
			if count == 0:
				del self._content[package]
			else:
				self._content[package] = count
		except KeyError:
			raise OutOfStockError()

		return package

	def __str__(self):
		return "WAREHOUSE [{} : {}]".format(self.name, str(self._content))

	def __repr__(self):
		return str(self)

	def __contains__(self, item):
		return item in self._content

class Grid(object):
	def __init__(self, width, height):
		self.width = width
		self.height = height
		self._grid = [[_Cell() for i in range(self.height)] for j in range(self.width)]
		self._items = {}

	def placeWarehouse(self, warehouse, pos):
		self._grid[pos.x][pos.y].addWarehouse(warehouse)
		self._items[warehouse] = pos

	def placeDrone(self, drone, pos):
		self._grid[pos.x][pos.y].addDrone(drone)
		self._items[drone] = pos

	def placeCustomer(self, customer, pos):
		self._grid[pos.x][pos.y].addCustomer(customer)
		self._items[customer] = pos

	def warehousesAt(self, pos):
		return self._grid[pos.x][pos.y].warehouses

	def dronesAt(self, pos):
		return self._grid[pos.x][pos.y].drones

	def customersAt(self, pos):
		return self._grid[pos.x][pos.y].customers

	def unplace(self, item):
		pos = self._items[item]
		del self._items[item]
		self._grid[pos.x][pos.y].remove(item)

	def display(self):
		for i in range(self.height):
			for j in range(self.width):
				print self._grid[j][i],
			print

	def __iter__(self):
		for i in range(self.height):
			for j in range(self.width):
				yield Position(j, i)

class _Cell(object):
	def __init__(self):
		self.customers = []
		self.warehouses = []
		self.drones = []

	def addCustomer(self, customer):
		self.customers.append(customer)

	def addWarehouse(self, warehouse):
		self.warehouses.append(warehouse)

	def addDrone(self, drone):
		self.drones.append(drone)

	def remove(self, item):
		for collection in [self.customers, self.warehouses, self.drones]:
			try:
				collection.remove(item)
				break
			except ValueError:
				pass

	def __str__(self):
		return "C{}W{}D{}".format(len(self.customers), len(self.warehouses), len(self.drones))

class Simulation(object):
	def __init__(self, grid, warehouses, orders, drones, timelimit):
		self.grid = grid
		self.warehouses = warehouses
		for warehouse in self.warehouses:
			self.grid.placeWarehouse(warehouse, warehouse.position)

		self.orders = _OrderManager(orders)
		for order in self.orders:
			if order.customer not in self.grid.customersAt(order.customer.position):
				self.grid.placeCustomer(order.customer, order.customer.position)

		self._drones = {drone : 0 for drone in drones}
		for drone in self._drones:
			self.grid.placeDrone(drone, drone.position)

		self.timelimit = timelimit

	@property
	def drones(self):
		return self._drones.keys()

	@property
	def cost(self):
		return max(self._drones.values())

	def droneCost(self, drone):
		return self._drones[drone]

	def flyDroneTo(self, drone, pos):
		self.grid.unplace(drone)
		self._drones[drone] += drone.flyTo(pos)
		self.grid.placeDrone(drone, drone.position)

	def warehousesContaining(self, package):
		return [wh for wh in self.warehouses if package in wh]

	def claimOrder(self, order):
		self.orders.remove(order)

	def completeOrder(self, order):
		if not self.orders.hasCustomer(order.customer):
			self.grid.unplace(order.customer)

	def display(self):
		self.grid.display()

class _OrderManager(object):
	def __init__(self, orders):
		self._orders = list(orders)

	def remove(self, order):
		self._orders.remove(order)

	def hasCustomer(self, customer):
		return any(order.customer == customer for order in self)

	def __getitem__(self, index):
		return self._orders[index]

	def __len__(self):
		return len(self._orders)

	def __iter__(self):
		for order in self._orders:
			yield order

	def __nonzero__(self):
		return len(self) > 0

def loadSimulation():
	warehouses = []
	with open("warehouses.json") as warehousesFile:
		content = json.loads(warehousesFile.read())
		for warehouseName in content:
			pos = Position(*content[warehouseName]["position"])
			packages = sum(([Package(packageName)] * count for packageName, count in content[warehouseName]["packages"]), [])
			warehouses.append(Warehouse(warehouseName, pos, packages))

	orders = []
	with open("orders.json") as ordersFile:
		content = json.loads(ordersFile.read())
		for customerName in content:
			customer = Customer(customerName, Position(*content[customerName]["position"]))
			packages = [Package(packageName) for packageName in content[customerName]["packages"]]
			orders.append(Order(customer, packages))

	with open("settings.json") as settingsFile:
		content = json.loads(settingsFile.read())
		grid = Grid(content["width"], content["height"])
		drones = [Drone("Drone{}".format(i), Position(0,0)) for i in range(content["drones"])]
		timelimit = content["timelimit"]
	
	return Simulation(grid, warehouses, orders, drones, timelimit)

def randomSolve(simulation, visualize = lambda grid : None):
	while simulation.orders:
		drone = random.choice(simulation.drones)
		order = random.choice(simulation.orders)
		simulation.claimOrder(order)
		
		for package in order.packages:
			warehouse = random.choice(simulation.warehousesContaining(package))
			
			simulation.flyDroneTo(drone, warehouse.position)
			visualize(simulation.grid)
			simulation.flyDroneTo(drone, order.customer.position)
			visualize(simulation.grid)
	
def greedySolve(simulation, visualize = lambda grid : None):
	while simulation.orders:
		drone = random.choice(simulation.drones)
		order = random.choice(simulation.orders)
		simulation.claimOrder(order)
		
		for package in order.packages:
			warehouse = min(simulation.warehousesContaining(package), key = lambda wh : drone.distanceTo(wh.position))
			
			simulation.flyDroneTo(drone, warehouse.position)
			warehouse.retrieve(package)
			visualize(simulation.grid)
			simulation.flyDroneTo(drone, order.customer.position)
			visualize(simulation.grid)

		simulation.completeOrder(order)

if __name__ == "__main__":
	simulation = loadSimulation()
	simulation.display()
	visualisation.visualize(simulation.grid)
	
	greedySolve(simulation, visualize = visualisation.visualize)
	print "Total cost : {}".format(simulation.cost)