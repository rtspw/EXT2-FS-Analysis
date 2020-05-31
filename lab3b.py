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

if __name__ == '__main__':
    filename = process_arguments(sys.argv)
    process_ext2_report(filename)

