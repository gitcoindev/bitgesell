#!/usr/bin/env python3
# Copyright (c) 2019-2020 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test that we reject low difficulty headers to prevent our block tree from filling up with useless bloat"""

from test_framework.messages import (
    CBlockHeader,
    from_hex,
)
from test_framework.p2p import (
    P2PInterface,
    msg_headers,
)
from test_framework.test_framework import BGLTestFramework

import os


class RejectLowDifficultyHeadersTest(BGLTestFramework):
    def set_test_params(self):
        self.setup_clean_chain = True
        self.chain = 'testnet3'  # Use testnet chain because it has an early checkpoint
        self.num_nodes = 2

    def add_options(self, parser):
        parser.add_argument(
            '--datafile',
            default='data/blockheader_testnet3.hex',
            help='Test data file (default: %(default)s)',
        )

    def run_test(self):
        self.log.info("Read headers data")
        self.headers_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.options.datafile)
        with open(self.headers_file_path, encoding='utf-8') as headers_data:
            h_lines = [l.strip() for l in headers_data.readlines()]

        # The headers data is taken from testnet3 for early blocks from genesis until the first checkpoint. There are
        # two headers with valid POW at height 1 and 2, forking off from genesis. They are indicated by the FORK_PREFIX.
        FORK_PREFIX = 'fork:'
        self.headers = [l for l in h_lines if not l.startswith(FORK_PREFIX)]
        self.headers_fork = [l[len(FORK_PREFIX):] for l in h_lines if l.startswith(FORK_PREFIX)]

        self.headers = [from_hex(CBlockHeader(), h) for h in self.headers]
        self.log.debug("First two decoded headers")
        
        for h in self.headers[:2]:
            self.log.debug(h)
        self.log.debug("First two decoded fork headers")

        self.headers_fork = [from_hex(CBlockHeader(), h) for h in self.headers_fork]
        
        for h in self.headers_fork[:2]:
            self.log.debug(h)

        # now tampering the headers
        import copy
        #self.headers_fork[0].hashPrevBlock = self.headers[0].hashPrevBlock
        #self.headers_fork[0].hashMerkleRoot = self.headers[0].hashMerkleRoot
        #self.headers_fork[0].rehash()
        self.headers_fork[1].hashPrevBlock = 0xcf3f6805ed137f0dc12560df1a7e63bba5bbcacfdd92d4852a50942083afbc22
        self.headers_fork[1].hashMerkleRoot = 0xf1922df2de3a5f92fce244750af8a8374e714593c9a92d09cf41f694f465bc21
        
        #self.headers_fork[1].rehash()
        #self.log.debug("Deep copied to")
        #fork_hdr = copy.deepcopy(self.headers_fork[1])
        #self.log.debug(fork_hdr)
        #fork_hdr.rehash()
        #serialized_fork_hdr = fork_hdr.serialize()
        #self.log.debug(serialized_fork_hdr.hex())
        self.log.debug(self.nodes[0].getblockheader("00000018cdcfeeb4dfdebe9392b855cfea7d6ddb953ef13f974b58773606d53d", True))
        self.log.info("Feed all non-fork headers, including and up to the first checkpoint")
        peer_checkpoint = self.nodes[0].add_p2p_connection(P2PInterface())
        peer_checkpoint.send_and_ping(msg_headers(self.headers))
        self.log.debug("#####################################")
        self.log.debug(self.nodes[0].getchaintips())
       
        assert {
            'height': 546,
            'hash': '000000033f0ecd6bc1c46eb98a2856cf2fe48bc3e90ef11ac24ea5272c1adbf8',
            'branchlen': 546,
            'status': 'headers-only',
        } in self.nodes[0].getchaintips()

        self.log.info("Feed all fork headers (fails due to checkpoint)")
        with self.nodes[0].assert_debug_log(['bad-fork-prior-to-checkpoint']):
        #with self.nodes[0].assert_debug_log(['missing prev block']):
            self.log.debug('checking bad-fork-prior-to-checkpoint found correctly')
            self.log.debug(self.headers_fork)
            peer_checkpoint.send_message(msg_headers(self.headers_fork))
            #peer_checkpoint.wait_for_disconnect()

        self.log.info("Feed all fork headers (succeeds without checkpoint)")
        # On node 0 it succeeds because checkpoints are disabled
        self.restart_node(0, extra_args=['-nocheckpoints'])
        peer_no_checkpoint = self.nodes[0].add_p2p_connection(P2PInterface())
        peer_no_checkpoint.send_and_ping(msg_headers(self.headers_fork))
        self.log.debug(self.nodes[0].getchaintips())
        assert {
            "height": 2,
            "hash": "00000000b0494bd6c3d5ff79c497cfce40831871cbf39b1bc28bd1dac817dc39",
            "branchlen": 2,
            "status": "headers-only",
        } in self.nodes[0].getchaintips()

        # On node 1 it succeeds because no checkpoint has been reached yet by a chain tip
        peer_before_checkpoint = self.nodes[1].add_p2p_connection(P2PInterface())
        peer_before_checkpoint.send_and_ping(msg_headers(self.headers_fork))
        assert {
            "height": 2,
            "hash": "00000000b0494bd6c3d5ff79c497cfce40831871cbf39b1bc28bd1dac817dc39",
            "branchlen": 2,
            "status": "headers-only",
        } in self.nodes[1].getchaintips()


if __name__ == '__main__':
    RejectLowDifficultyHeadersTest().main()
