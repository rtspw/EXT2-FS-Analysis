# NAME: Richard Tang
# EMAIL: richardcxtang@ucla.edu
# ID: 305348008

from enum import Enum
import sys
import csv

class Exit_Code(Enum):
    NO_INCONSISTENCIES = 0
    PROGRAM_ERROR = 1
    INCONSISTENCIES_FOUND = 2

class EXT2_Filesystem():
    def __init__(self):
        self.num_of_blocks = None 
        self.num_of_inodes = None 
        self.block_size = None
        self.inode_size = None
        self.free_blocks = []
        self.free_inodes = []
        self.inodes = {}
        self.directories = {}
        self.indirect_blocks = {}

class EXT2_Inode():
    def __init__(self, filetype, link_count, direct_blocks = None, indir_block = None, double_indir_block = None, triple_indir_block = None):
        self.filetype = filetype
        self.link_count = link_count
        self.direct_blocks = direct_blocks
        self.indir_block = indir_block
        self.double_indir_block = double_indir_block
        self.triple_indir_block = triple_indir_block

class EXT2_Dirent():
    def __init__(self, parent_inode, logical_offset, file_inode, name):
        self.parent_inode = parent_inode
        self.logical_offset = logical_offset
        self.file_inode = file_inode
        self.name = name

class EXT2_Indirect_Block():
    def __init__(self, parent_inode, depth, logical_offset, block_num, referenced_block_num):
        self.parent_inode = parent_inode
        self.depth = depth
        self.logical_offset = logical_offset
        self.block_num = block_num
        self.referenced_block_num = referenced_block_num

def print_usage_string(program_name):
    print('Usage: {} filename'.format(program_name))

def process_arguments(arguments):
    if (len(arguments) != 2):
        program_name = arguments[0]
        print_usage_string(arguments[0])
        sys.exit(Exit_Code.PROGRAM_ERROR.value)
    filename = arguments[1]
    return filename

def process_ext2_report(filename):
    fs_instance = EXT2_Filesystem()
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='\'')
        for row in reader:
            line_type, *data = row
            if (line_type == 'BFREE'):
                free_block_num = int(data[0])
                fs_instance.free_blocks.append(free_block_num)
            elif (line_type == 'IFREE'):
                free_inode_num = int(data[0])
                fs_instance.free_inodes.append(free_inode_num)
            elif (line_type == 'SUPERBLOCK'):
                num_of_blocks, num_of_inodes, block_size, inode_size, *_ = data
                fs_instance.num_of_blocks = num_of_blocks
                fs_instance.num_of_inodes = num_of_inodes
                fs_instance.block_size = block_size
                fs_instance.inode_size = inode_size
            elif (line_type == 'INODE'):
                inode_num = data[0]
                file_type = data[1]
                link_count = data[5]
                if (file_type != 's'):
                    *direct_blocks, indir, d_indir, t_indir = data[11:]
                    fs_instance.inodes[inode_num] = EXT2_Inode(file_type, link_count, direct_blocks, indir, d_indir, t_indir)
                else:
                    fs_instance.inodes[inode_num] = EXT2_Inode(file_type, link_count)
            elif (line_type == 'DIRENT'):
                parent_inode, logical_offset, file_inode, _, _, name = data
                if (parent_inode not in fs_instance.directories):
                    fs_instance.directories[parent_inode] = []
                fs_instance.directories[parent_inode].append(EXT2_Dirent(parent_inode, logical_offset, file_inode, name))
            elif (line_type == 'INDIRECT'):
                parent_inode, depth, logical_offset, block_num, ref_block_num = data
                if (parent_inode not in fs_instance.indirect_blocks):
                    fs_instance.indirect_blocks[parent_inode] = []
                fs_instance.indirect_blocks[parent_inode].append(EXT2_Indirect_Block(parent_inode, depth, logical_offset, block_num, ref_block_num))

    process_inode_allocation_audit(fs_instance)
    process_directory_consistency_audit(fs_instance)

def process_inode_allocation_audit(fs_instance):
    """
    Checks for I-node allocation inconsistencies.
    Prints all inconsistencies to standard output.
    """
    inodes_allocation_list = [False] * (int(fs_instance.num_of_inodes) + 1)

    # Place free inodes on table
    for free_inode in fs_instance.free_inodes:
        inodes_allocation_list[free_inode] = True

    for inode_number in fs_instance.inodes:
        if (inodes_allocation_list[int(inode_number)]):
            print('ALLOCATED INODE {0} ON FREELIST'.format(inode_number))
            # TODO: inconsistencies found
        else:
            inodes_allocation_list[int(inode_number)] = True

    reserved_inodes = [1, 3, 4, 5, 6, 7, 8, 9, 10]
    for inode_number in reserved_inodes:
        inodes_allocation_list[inode_number] = True

    for index, inode_allocated in enumerate(inodes_allocation_list[1:], 1):
        if (not inode_allocated):
            print('UNALLOCATED INODE {0} NOT ON FREELIST'.format(index))
            # TODO: inconsistencies found

def process_directory_consistency_audit(fs_instance):
    """
    Checks for directory inconsistencies.
    Prints all inconsistencies to standard output.
    """
    reference_counts = {}
    for directory in fs_instance.directories.values():
        for directory_entry in directory:
            file_inode = directory_entry.file_inode
            if (file_inode not in reference_counts):
                reference_counts[file_inode] = 0
            reference_counts[file_inode] = reference_counts[file_inode] + 1

    for inode_number in fs_instance.inodes:
        link_count = fs_instance.inodes[inode_number].link_count
        if (inode_number not in reference_counts):
            reference_count = 0
        else:
            reference_count = reference_counts[inode_number]
        if int(link_count) != reference_count:
            print('INODE {0} HAS {1} LINKS BUT LINKCOUNT IS {2}'.format(inode_number, reference_count, link_count))
            # TODO: inconsistencies found

    unallocated_inodes = set()
    for inode_number in fs_instance.free_inodes:
        unallocated_inodes.add(inode_number)
    for inode in fs_instance.inodes:
        if (int(inode) in unallocated_inodes):
            unallocated_inodes.remove(int(inode))

    for directory_inode in fs_instance.directories:
        for directory_entry in fs_instance.directories[directory_inode]:
            file_inode = int(directory_entry.file_inode)
            if (file_inode < 1 or file_inode > int(fs_instance.num_of_inodes) + 1):
                print('DIRECTORY INODE {0} NAME \'{1}\' INVALID INODE {2}'.format(directory_inode, directory_entry.name, file_inode))
                # TODO: inconsistencies found
            if (file_inode in unallocated_inodes):
                print('DIRECTORY INODE {0} NAME \'{1}\' UNALLOCATED INODE {2}'.format(directory_inode, directory_entry.name, file_inode))
                # TODO: inconsistencies found
            if (directory_entry.name == '.'):
                if (int(directory_inode) != file_inode):
                    print('DIRECTORY INODE {0} NAME \'{1}\' LINK TO INODE {2} SHOULD BE {0}'.format(directory_inode, directory_entry.name, file_inode))
                    # TODO: inconsistencies found
            elif (directory_entry.name == '..'):
                pass  # TODO: is this case needed?

    for directory_entry in fs_instance.directories['2']:
        if (directory_entry.name == '..'):
            if (directory_entry.file_inode != '2'):
                print('DIRECTORY INODE 2 NAME \'..\' LINK TO INODE {0} SHOULD BE 2'.format(directory_entry.file_inode))
                # TODO: inconsistencies found
            break

if __name__ == '__main__':
    filename = process_arguments(sys.argv)
    process_ext2_report(filename)

