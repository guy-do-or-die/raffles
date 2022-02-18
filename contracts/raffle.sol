// SPDX-License-Identifier: MIT

pragma solidity ^0.8.7;

import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";
import "@openzeppelin/contracts/access/Ownable.sol";


/**
 * @title Raffle
 * @dev Raffle contract
 */
contract Raffle is VRFConsumerBase, Ownable {

    uint256 constant ENTRIES_LIMIT = 100;

    enum STATE {
        CREATED,
        RAFFLING,
        DONE
    }

    STATE public state;

    mapping(uint256 => address) public entries;
    mapping(uint256 => address) public winners;

    uint256 public entriesNumber;
    uint256 public winnersNumber;

    bytes32 private _keyHash;
    uint256 private _fee;

    bytes32 private _requestId;
    uint256 private _randomness;
    
    event RequestedRandomness(bytes32 requestId);
    event ReceivedRandomness(bytes32 requestId);

    constructor(address VRF, address LINK, bytes32 KEY, uint256 FEE) VRFConsumerBase(VRF, LINK) {
        _fee = FEE;
        _keyHash = KEY;

        state = STATE.CREATED;
    }

    /**
     * Callback function used by VRF Coordinator
     */
    function fulfillRandomness(bytes32 requestId, uint256 randomness) internal override {
        emit ReceivedRandomness(requestId);
        setWinners(randomness);

        state = STATE.DONE;
    }

    /**
     * Set winners
     * @param randomness source of randomness
     */
    function setWinners(uint256 randomness) private {
        uint256 chunk = entriesNumber / winnersNumber;
        uint256 edge = chunk * winnersNumber;
        uint256 offset = 0;
        uint256 winner;

        while (offset < entriesNumber) {
            
            if (offset + chunk == edge) {
                chunk = entriesNumber - offset;
            }

            winner = offset + uint256(keccak256(abi.encode(randomness, offset))) % chunk;
            winners[winner] = address(entries[winner]);
            offset += chunk;
        }
    }

    /**
     * @dev Set the raffle entries
     * @param _addresses entries to store
     * @param _overwrite overwrite entries
     */
    function addEntries(address[] memory _addresses, bool _overwrite) external onlyOwner {
        require(state == STATE.CREATED, "Raffle is already initiated");
        require(_addresses.length < ENTRIES_LIMIT, "Too many entries, use multiple transactions");

        uint256 start = entriesNumber;

        if (_overwrite) {
            if (_addresses.length < entriesNumber) {
                for(uint256 i = _addresses.length; i < entriesNumber; i++) {
                    entries[i] = address(0x0);
                }
            }

            start = 0;
            entriesNumber = 0;
        }

        for(uint256 i = 0; i < _addresses.length; i++) {
            entries[start + i] = _addresses[i];
            entriesNumber++;
        }
    }

    /**
     * @dev Make a raffle
     * @param _number number of winners to raffle
     */
    function selectWinners(uint256 _number) external onlyOwner {
        require(state == STATE.CREATED, "Raffle is already initiated");
        require(0 < _number && _number < entriesNumber, "Number of winners should be positive and less than number of entries");
        require(LINK.balanceOf(address(this)) >= _fee, "Not enough LINK");

        winnersNumber = _number;
        
        _requestId = requestRandomness(_keyHash, _fee);
        emit RequestedRandomness(_requestId);

        state = STATE.RAFFLING;
    }
    
}
