# NAME: Richard Tang, Victor Tang
# EMAIL: richardcxtang@ucla.edu, victorwtang@g.ucla.edu
# ID: 305348008, 005359343

from enum import Enum
import sys
import csv
import math

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
        self.free_block_bitmap_index = None
        self.free_inode_bitmap_index = None
        self.first_inode_index = None
        self.free_blocks = set()
        self.free_inodes = set()
        self.referenced_blocks = set()
        self.duplicate_blocks = set()
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

global_exit_code = Exit_Code.NO_INCONSISTENCIES

def set_global_exit_code():
    global global_exit_code
    global_exit_code = Exit_Code.INCONSISTENCIES_FOUND

def print_usage_string(program_name):
    print('Usage: {} filename'.format(program_name))

def process_arguments(arguments):
    if (len(arguments) != 2):
        program_name = arguments[0]
        print_usage_string(program_name)
        sys.exit(Exit_Code.PROGRAM_ERROR.value)
    filename = arguments[1]
    return filename

def process_ext2_report(filename):
    """
    Scans the CSV report and adds it to EXT2_Filesystem instance data structure
    For each row, it checks the first entry for the line type, then puts the
    remaining data in the appropriate data structure. 
    Returns the filesystem structure instance.
    """
    fs_instance = EXT2_Filesystem()
    with open(filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='\'')
        for row in reader:
            line_type, *data = row

            if (line_type == 'BFREE'):
                free_block_num = int(data[0])
                fs_instance.free_blocks.add(free_block_num)

            elif (line_type == 'IFREE'):
                free_inode_num = int(data[0])
                fs_instance.free_inodes.add(free_inode_num)

            elif (line_type == 'SUPERBLOCK'):
                num_of_blocks, num_of_inodes, block_size, inode_size, *_ = data
                fs_instance.num_of_blocks = num_of_blocks
                fs_instance.num_of_inodes = num_of_inodes
                fs_instance.block_size = block_size
                fs_instance.inode_size = inode_size

            elif (line_type == 'GROUP'):
                *_, free_block_bitmap, free_inode_bitmap, first_inode_index = data
                fs_instance.free_block_bitmap_index = int(free_block_bitmap)
                fs_instance.free_inode_bitmap_index = int(free_inode_bitmap)
                fs_instance.first_inode_index = int(first_inode_index)

            elif (line_type == 'INODE'):
                inode_num = data[0]
                file_type = data[1]
                link_count = data[5]
                if (len(data[11:]) == 0):
                    fs_instance.inodes[inode_num] = EXT2_Inode(file_type, link_count)
                else:
                    *direct_blocks, indir, d_indir, t_indir = data[11:]
                    for direct_block in direct_blocks:
                        if (direct_block in fs_instance.referenced_blocks):
                            fs_instance.duplicate_blocks.add(direct_block)
                        fs_instance.referenced_blocks.add(direct_block)
                    if (indir in fs_instance.referenced_blocks):
                        fs_instance.duplicate_blocks.add(indir)
                    fs_instance.referenced_blocks.add(indir)
                    if (d_indir in fs_instance.referenced_blocks):
                        fs_instance.duplicate_blocks.add(d_indir)
                    fs_instance.referenced_blocks.add(d_indir)
                    if (t_indir in fs_instance.referenced_blocks):
                        fs_instance.duplicate_blocks.add(t_indir)
                    fs_instance.referenced_blocks.add(t_indir)
                    fs_instance.inodes[inode_num] = EXT2_Inode(file_type, link_count, direct_blocks, indir, d_indir, t_indir)

            elif (line_type == 'DIRENT'):
                parent_inode, logical_offset, file_inode, _, _, name = data
                if (parent_inode not in fs_instance.directories):
                    fs_instance.directories[parent_inode] = []
                fs_instance.directories[parent_inode].append(EXT2_Dirent(parent_inode, logical_offset, file_inode, name))
            
            elif (line_type == 'INDIRECT'):
                parent_inode, depth, logical_offset, block_num, ref_block_num = data
                if (parent_inode not in fs_instance.indirect_blocks):
                    fs_instance.indirect_blocks[parent_inode] = []
                if (ref_block_num in fs_instance.referenced_blocks):
                    fs_instance.duplicate_blocks.add(ref_block_num)
                fs_instance.referenced_blocks.add(ref_block_num)
                fs_instance.indirect_blocks[parent_inode].append(EXT2_Indirect_Block(parent_inode, depth, logical_offset, block_num, ref_block_num))
    
    return fs_instance
    
def get_first_non_reserved_block(fs_instance):
    """
    Gets the index of the first block after the inode tables
    """
    inodes_per_block = int(fs_instance.inode_size) / int(fs_instance.block_size)
    inode_table_block_length = math.ceil(inodes_per_block * int(fs_instance.num_of_inodes))
    first_non_reserved_block = fs_instance.first_inode_index + inode_table_block_length
    return first_non_reserved_block

def is_reserved_block(fs_instance, block_num):
    """
    Checks if the given block number is reserved (superblock, group summary, free-lists, etc.)
    """
    first_non_reserved_block = get_first_non_reserved_block(fs_instance)
    return int(block_num) < first_non_reserved_block

def get_logical_offset(fs_instance, depth = 0, direct_block_index = None):
    """
    Calculates the logical offset (block offset treating the file as continuous) using
    the depth (indirectness).
    """
    if (depth == 0): return direct_block_index
    num_of_entries = int(fs_instance.block_size) // 4
    direct_block_size = 12
    if (depth == 1):
        return direct_block_size
    indirect_block_size = num_of_entries
    if (depth == 2):
        return indirect_block_size + direct_block_size
    double_indir_block_size = num_of_entries * num_of_entries
    if (depth == 3):
        return double_indir_block_size + indirect_block_size + direct_block_size
    return -1


def check_block_consistency(fs_instance, inode_num, block_num, depth = 0, direct_block_index = None):
    """
    Given a block number under a parent inode, checks to see if blocks are valid and not reserved.
    Also checks if there are duplicate block entries.
    Inconsistencies are printed to standard output.
    If the block number is a direct block, direct_block_index gives the logical offset.
    """
    if (block_num == 0): return
    block_type = (['', 'INDIRECT ', 'DOUBLE INDIRECT ', 'TRIPLE INDIRECT '])[depth]
    logical_offset = get_logical_offset(fs_instance, depth, direct_block_index)
    if (block_num < 0 or block_num >= int(fs_instance.num_of_blocks)):
        print('INVALID {0}BLOCK {1} IN INODE {2} AT OFFSET {3}'.format(block_type, block_num, inode_num, logical_offset))
        set_global_exit_code()
    if (is_reserved_block(fs_instance, block_num)):
        print('RESERVED {0}BLOCK {1} IN INODE {2} AT OFFSET {3}'.format(block_type, block_num, inode_num, logical_offset))
        set_global_exit_code()
    if (str(block_num) in fs_instance.duplicate_blocks):
        print('DUPLICATE {0}BLOCK {1} IN INODE {2} AT OFFSET {3}'.format(block_type, block_num, inode_num, logical_offset))
        set_global_exit_code()
    
def check_block_free_list_consistency(fs_instance):
    """
    Checks that all blocks are either in the free list or allocated but not both or neither.
    Prints all inconsistencies to standard output.
    """
    first_non_reserved_block = get_first_non_reserved_block(fs_instance)
    for block_num in range(first_non_reserved_block, int(fs_instance.num_of_blocks)):
        if (block_num in fs_instance.free_blocks and str(block_num) in fs_instance.referenced_blocks):
            print('ALLOCATED BLOCK {0} ON FREELIST'.format(block_num))
            set_global_exit_code()
        if (block_num not in fs_instance.free_blocks and str(block_num) not in fs_instance.referenced_blocks):
            print('UNREFERENCED BLOCK {0}'.format(block_num))
            set_global_exit_code()
    
def process_block_consistency_audit(fs_instance):
    """
    Checks if all block pointers are valid and block free-list is consistent.
    Prints all inconsistencies to standard output. 
    """
    for inode_num, inode in fs_instance.inodes.items():
        if (inode.filetype == 's'): continue
        for index, direct_block in enumerate(inode.direct_blocks):
            check_block_consistency(fs_instance, inode_num, int(direct_block), 0, index)
        check_block_consistency(fs_instance, inode_num, int(inode.indir_block), 1)
        check_block_consistency(fs_instance, inode_num, int(inode.double_indir_block), 2)
        check_block_consistency(fs_instance, inode_num, int(inode.triple_indir_block), 3)
    check_block_free_list_consistency(fs_instance)


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
            set_global_exit_code()
        else:
            inodes_allocation_list[int(inode_number)] = True

    reserved_inodes = [1, 3, 4, 5, 6, 7, 8, 9, 10]
    for inode_number in reserved_inodes:
        inodes_allocation_list[inode_number] = True

    for index, inode_allocated in enumerate(inodes_allocation_list[1:], 1):
        if (not inode_allocated):
            print('UNALLOCATED INODE {0} NOT ON FREELIST'.format(index))
            set_global_exit_code()

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
            set_global_exit_code()

    unallocated_inodes = set()
    for inode_number in fs_instance.free_inodes:
        unallocated_inodes.add(inode_number)
    for inode in fs_instance.inodes:
        if (int(inode) in unallocated_inodes):
            unallocated_inodes.remove(int(inode))

    parent_directories = {}
    for directory_inode in fs_instance.directories:
        for directory_entry in fs_instance.directories[directory_inode]:
            if (directory_entry.name != '..' and directory_entry.name != '.'):
                parent_directories[directory_entry.file_inode] = directory_inode
    parent_directories['2'] = '2'

    for directory_inode in fs_instance.directories:
        for directory_entry in fs_instance.directories[directory_inode]:
            file_inode = int(directory_entry.file_inode)
            if (file_inode < 1 or file_inode > int(fs_instance.num_of_inodes) + 1):
                print('DIRECTORY INODE {0} NAME \'{1}\' INVALID INODE {2}'.format(directory_inode, directory_entry.name, file_inode))
                set_global_exit_code()
            if (file_inode in unallocated_inodes):
                print('DIRECTORY INODE {0} NAME \'{1}\' UNALLOCATED INODE {2}'.format(directory_inode, directory_entry.name, file_inode))
                set_global_exit_code()
            if (directory_entry.name == '.'):
                if (int(directory_inode) != file_inode):
                    print('DIRECTORY INODE {0} NAME \'{1}\' LINK TO INODE {2} SHOULD BE {0}'.format(directory_inode, directory_entry.name, file_inode))
                    set_global_exit_code()
            elif (directory_entry.name == '..'):
                parent_inode = int(parent_directories[directory_inode])
                if (file_inode != parent_inode):
                    print('DIRECTORY INODE {0} NAME \'..\' LINK TO INODE {1} SHOULD BE {2}'.format(directory_inode, file_inode, parent_inode))
                    set_global_exit_code()

if __name__ == '__main__':
    filename = process_arguments(sys.argv)
    fs_instance = process_ext2_report(filename)
    process_block_consistency_audit(fs_instance)
    process_inode_allocation_audit(fs_instance)
    process_directory_consistency_audit(fs_instance)
    sys.exit(global_exit_code.value)
