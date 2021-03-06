#!/usr/bin/python
# -*- coding: UTF-8 -*-
import random
NODE_NUM = 250


def helper_find_smallest_pair(l, n):
    """helper function to find the smallest difference in a sorted list

    return: the index pair
    """
    r1 = n-1
    r2 = 0
    diff = min(l[r1][1]-l[r2][1], 1+l[r2][1]-l[r1][1])
    for i in range(n-1):
        new_diff = min(diff, l[i+1][1]-l[i][1])
        if new_diff != diff:
            r1 = i
            r2 = i+1
            diff = new_diff
    return (r1, r1)


def BRC_generation(N):
    coordinates = []
    coordinates.append((0, random.uniform(0, 1)))  # n = 0
    a = coordinates[0][1]
    b = coordinates[0][1] + 1
    t = random.uniform(a+1/3, b-1/3)
    if t > 1:
        t -= 1
    coordinates.append((1, t))  # n = 1
    for n in range(1, N-1):  # n > 1
        coordinates.sort(key=lambda coord: coord[1])
        tr1, tr2 = helper_find_smallest_pair(coordinates, n)
        # not real r1 and r2, just the indexes of this sorted list

        if tr2 == n:  # it may be the last element
            tr1 = 0
            tr2 = n-1
        # print('Now tr1 is ', tr1, ' and tr2 is ', tr2)
        xr1 = coordinates[tr1][1]
        xr2 = coordinates[tr2][1]
        if xr2 - xr1 > 1/2:  # I reverse the condition in paper
            a = xr1
            b = xr2
        else:
            a = xr2
            b = xr1+1
        t = random.uniform(a+1/3/n, b-1/3/n)
        if t > 1:
            t -= 1
        coordinates.append((n+1, t))
    coordinates.sort(key=lambda coord: coord[1])
    # coordinates.sort(key=lambda coord: coord[0])
    return coordinates


class FakePacket(object):
    """
    """

    def __init__(self, src, dst):
        self.src = src
        self.dst_coordinates = dst.coordinates
        # self.src = (src_ip, src_port)
        # self.dst = (dst_ip, dst_port)
        # self.protocol_type = protocol_type
        self.path_dis = 0


class S2Node(object):
    """The Space Shuffle Node Class
    """
    counter = 0

    def __init__(self, stored_hops=1, server_IDs=None):
        """Initialize the node with IDs of servers and coordinates of self&neighbours

        Args:
            servers - array of IDs
            coordinates - array of coordinates in different space
        """
        S2Node.counter += 1
        self.ID = S2Node.counter
        self.servers = server_IDs  # useless in this version
        self.coordinates = []
        self.neighbours = []
        # self.further_neighbour_groups = []
        self.stored_neighbors = [[]]  # K-ary tree
        self.stored_hops = stored_hops
        # self.free_neighbours = []
        # self.repeated_neighbours = []  # log to avoid repeated connection

    def join_a_new_virtual_ring(self, coordinate):
        self.coordinates.append(coordinate)

    def add_neighbour(self, new_neighbour):
        if new_neighbour not in self.neighbours:
            self.neighbours.append(new_neighbour)
            self.stored_neighbors[0].append(new_neighbour)
            return True
        return False
        # if new_neighbour in self.repeated_neighbours:
        #     pass
        # elif new_neighbour in self.neighbours:
        #     self.repeated_neighbours.append(new_neighbour)
        # else:
        #     self.neighbours.append(new_neighbour)

    def get_free_port_number(self):
        return 2*self.coordinates.__len__() - self.neighbours.__len__()

    def update_routing_tables(self):
        hops = self.stored_hops
        while hops > 1:
            self.stored_neighbors.append([])  # add a new level
            for neighbour in self.stored_neighbors[-2]:
                self.stored_neighbors[-1] += neighbour.neighbours  # repeatition
            hops -= 1

    def __cal_CD(self, dst_coordinates):
        CD = []
        for x, y in zip(self.coordinates, dst_coordinates):
            CD.append(min(abs(x-y), 1-abs(x-y)))
        return CD

    def __cal_hash(self, pkt):
        pass

    def cal_MCD(self, dst_coordinates):
        CD = self.__cal_CD(dst_coordinates)
        CD.sort()
        return CD[0]

    def forward(self, pkt, mp_enabled=False):
        """Forward the packet delivered to this switch

        Returns: the path length of a sucessful delivered paket
        """
        if mp_enabled and pkt.src is self:  # first hop
            V = []
            for neighbour in self.neighbours:
                if neighbour.cal_MCD(pkt.dst_coordinates) < \
                   self.cal_MCD(pkt.dst_coordinates):
                    V.append(neighbour)
            return V[self.__cal_hash(pkt)].forwarding(pkt)
        if pkt.path_dis > 255:
            raise Exception('Possible loop routing')
        # recursive fowarding, this is the exit condition
        if pkt.dst_coordinates == self.coordinates:
            return pkt.path_dis  # Successfully find the destination
        # assure that the forwarding is loop-free, otherwise it won't end
        else:
            pkt.path_dis += 1  # add one hop count in tha packet
            least_mcds = []
            for level, neighbours in enumerate(self.stored_neighbors):
                mcds = []
                for index, neighbour in enumerate(neighbours):
                    mcds.append((neighbour.cal_MCD(pkt.dst_coordinates), index))
                    # though executed by neighour node, we assume that the
                    # calculation happens in local; this will save the memory
                    # needed by simulation
                # print('Self Neighbour is', [n.ID for n in self.neighbours])
                # print('Neighbour is', [n.ID for n in neighbours])
                # print('Level:', level, 'MCDS:', mcds)
                mcds.sort(key=lambda mcd: mcd[0])  # sort by mcd results
                least_mcds.append((mcds[0][0], mcds[0][1], level))
            least_mcds.sort(key=lambda mcd: mcd[0])
            scale = self.neighbours.__len__()
            next_switch_index = int(least_mcds[0][1]/scale**least_mcds[0][2])
            return self.neighbours[next_switch_index].forward(pkt)

    def print_info(self):
        print('#', self.ID, 'S2 node info:')
        print('    coordinates:', self.coordinates)
        print('    neighour:', [ni.ID for ni in self.neighbours])
        print('    free_port_number:', self.get_free_port_number())


class S2Topo(object):
    """The Space Shuffle Topology Class

    "tell" nodes where they are and who their neighbours are
    """
    def __init__(self, N, L, d, hops=1):
        """Topology construction

        Args:
            N: the number of switches
            L: the number of virtual rings
            d: the number of actually using rings
            hops: how many hops' info will a node store
        """
        self.d = d
        self.nodes = [S2Node(hops) for i in range(N)]  # create N S2 nodes
        for i in range(L):
            reversed_ring = BRC_generation(N)
            ring = reversed_ring.copy()
            reversed_ring.reverse()
            last_v_id = ring[-1][0]
            last_rv_id = reversed_ring[-1][0]
            for (v_id, v_coord), (rv_id, rv_coord) in zip(ring, reversed_ring):
                # print("last_v_id", last_v_id, "last_rv_id", last_rv_id)
                self.nodes[v_id].join_a_new_virtual_ring(v_coord)
                self.nodes[v_id].add_neighbour(self.nodes[last_v_id])
                self.nodes[rv_id].add_neighbour(self.nodes[last_rv_id])
                last_v_id = v_id  # update for next
                last_rv_id = rv_id
        if self.__eliminate_free_ports():
            print('Perfect Topology!')
        else:
            print('Two free ports exists')
        for node in self.nodes:
            node.update_routing_tables()

    def __eliminate_free_ports(self):
        """Eliminating the free ports of switches by connecting them randomly
        due to the lack of a simple rollback operation, this function could not
        rule out the possibility that there is a switch with even free ports
        after port elimination.

        returns: whether the elimination is perfectly executed
        """
        port_pool = []
        for node in self.nodes:
            for i in range(node.get_free_port_number()):
                port_pool.append(node)
        print('Before port_pool:', [node.ID for node in port_pool])
        if port_pool == []:  # Can you believe? There is no free port
            print('Can you believe? There is no free port')
            return True
        while port_pool.__len__() > 3:  # 4 or more free ports
            i1, i2 = random.sample(range(port_pool.__len__()), 2)
            port_a, port_b = port_pool[i1], port_pool[i2]  # avoid index error
            if port_a is not port_b:
                re = port_a.add_neighbour(port_b)
                if re:
                    # not previously connected
                    port_b.add_neighbour(port_a)
                    i1 = port_pool.index(port_a)
                    del port_pool[i1]
                    i2 = port_pool.index(port_b)
                    del port_pool[i2]
        print('After port_pool:', [node.ID for node in port_pool])
        if port_pool[0] is not port_pool[1]:
            if port_pool[0].add_neighbour(port_pool[1]):
                port_pool[1].add_neighbour(port_pool[0])
                del port_pool
                return True
        return False

    def cal_path(self, ID_a, ID_b):
        src, dst = self.nodes[ID_a], self.nodes[ID_b]
        return src.forward(FakePacket(src, dst))

    def scales(self, number):
        pass

    def print_info(self):
        for node in self.nodes:
            node.print_info()


if __name__ == '__main__':
    # print(BRC_generation(20))
    topo = S2Topo(NODE_NUM, 5, 5, 2)
    # a, b = random.sample(range(10), 2)
    # print('The path length of this packet is', topo.cal_path(a, b))
    # topo.print_info()
    sum = 0
    connections = NODE_NUM*(NODE_NUM-1)/2
    for index_a in range(NODE_NUM):
        for index_b in range(index_a+1, NODE_NUM):
            sum += topo.cal_path(index_a, index_b)
    print('The average routing path length is', sum/connections)


# TO-DO
# [V] Enable next-hop storation
# [] First hop with hash fucntion
# [] Add support to choose only d spcace
# [] Plot the simulation results
