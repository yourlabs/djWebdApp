pragma solidity ^0.8.0;
import './FA12.sol';


contract Caller {
    event MintProxy(FA12 token);

    constructor() {}

    function mintProxy(FA12 token, address account, uint256 amount) public {
        token.mint(account, amount);
        emit MintProxy(token);
    }
}
