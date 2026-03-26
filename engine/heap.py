import heapq


class QuantelHeap:
    def __init__(self, size=10):
        # The pool of all available address numbers
        self.free_pool = list(range(size))
        heapq.heapify(self.free_pool)

        # The actual data storage: {address: value}
        self.memory = {}
        self.max_size = size

    def malloc(self, value):
        """Allocates a value and returns its address."""
        if not self.free_pool:
            raise RuntimeError("Heap Overflow: No memory left!")

        address = heapq.heappop(self.free_pool)
        self.memory[address] = value
        return address

    def free(self, address):
        """Removes data and puts the address back in the pool (creating a gap)."""
        if address in self.memory:
            del self.memory[address]
            heapq.heappush(self.free_pool, address)
        else:
            raise RuntimeError(f"Segmentation Fault: Invalid free at {address}")

    def get(self, address):
        if address not in self.memory:
            raise RuntimeError(f"Segmentation Fault: Accessing unallocated memory at {address}")
        return self.memory[address]

    def __repr__(self):
        """Visual map of the heap status."""
        map_str = "--- Heap Map ---\n"
        for i in range(self.max_size):
            status = self.memory.get(i, "[ FREE ]")
            map_str += f"[{i:02}]: {status}\n"
        return map_str