pragma solidity ^0.5.15;

contract Voting {
    address public owner;

    struct Candidate {
        uint id;
        string name;
        string party;
        uint voteCount;
    }

    mapping (uint => Candidate) public candidates;
    mapping (address => bool) public voters;

    uint public countCandidates;
    uint256 public votingEnd;
    uint256 public votingStart;

    event CandidateAdded(uint indexed id, string name, string party);
    event VoteCast(address indexed voter, uint indexed candidateID, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "Access restricted to election owner");
        _;
    }

    constructor() public {
        owner = msg.sender;
    }

    function addCandidate(string memory name, string memory party) public onlyOwner returns(uint) {
        countCandidates++;
        candidates[countCandidates] = Candidate(countCandidates, name, party, 0);
        emit CandidateAdded(countCandidates, name, party);
        return countCandidates;
    }

    function vote(uint candidateID) public {
        require((votingStart <= now) && (votingEnd > now), "Voting period is closed");
        require(candidateID > 0 && candidateID <= countCandidates, "Invalid candidate ID");
        require(!voters[msg.sender], "Voter has already cast a vote");

        voters[msg.sender] = true;
        candidates[candidateID].voteCount++;
        emit VoteCast(msg.sender, candidateID, now);
    }

    function checkVote() public view returns(bool) {
        return voters[msg.sender];
    }

    function getCountCandidates() public view returns(uint) {
        return countCandidates;
    }

    function getCandidate(uint candidateID) public view returns(uint, string memory, string memory, uint) {
        return (candidateID, candidates[candidateID].name, candidates[candidateID].party, candidates[candidateID].voteCount);
    }

    function setDates(uint256 _startDate, uint256 _endDate) public onlyOwner {
        require((_startDate + 1000000 > now) && (_endDate > _startDate), "Invalid date bounds");
        votingEnd = _endDate;
        votingStart = _startDate;
    }

    function closeElection() public onlyOwner {
        require(votingStart > 0, "Election has not started yet");
        votingEnd = now;
    }

    function getDates() public view returns (uint256, uint256) {
        return (votingStart, votingEnd);
    }
}
