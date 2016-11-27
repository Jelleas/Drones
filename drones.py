import math
import json
import visualisation
import dill
import time

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
	def __init__(self, customer, package):
		self.customer = customer
		self.package = package

	def __str__(self):
		return "ORDER [{} : {}]".format(self.customer, self.package)

	def __repr__(self):
		return str(self)


class Warehouse(object):
	def __init__(self, name, pos, packages):
		self.name = name
		self.position = pos
		packages = list(packages)
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

		self.drones = drones
		for drone in self.drones:
			self.grid.placeDrone(drone, drone.position)

		self.timelimit = timelimit


	def display(self):
		self.grid.display()

	def flyDroneTo(self, drone, pos):
		self.grid.unplace(drone)
		drone.flyTo(pos)
		self.grid.placeDrone(drone, drone.position)

class _OrderManager(object):
	def __init__(self, orders):
		self._orders = orders

	def __iter__(self):
		for order in self._orders:
			yield order

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
			orders.extend(Order(customer, package) for package in packages)

	with open("settings.json") as settingsFile:
		content = json.loads(settingsFile.read())
		grid = Grid(content["width"], content["height"])
		drones = [Drone("Drone{}".format(i), Position(0,0)) for i in range(content["drones"])]
		timelimit = content["timelimit"]
	
	return Simulation(grid, warehouses, orders, drones, timelimit)

if __name__ == "__main__":
	simulation = loadSimulation()
	simulation.display()

	visualisation.visualize(simulation.grid)
	time.sleep(1)
	simulation.flyDroneTo(simulation.drones[0], Position(5,5))
	visualisation.visualize(simulation.grid)
	