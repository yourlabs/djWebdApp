pragma solidity ^0.8.0;
import './FA12.sol';


contract Caller {
    event PreMintProxy(FA12 token);
    event PostMintProxy();

    constructor() {}

    function mintProxy(FA12 token, address account, uint256 amount) public {
        emit PreMintProxy(token);
        token.mint(account, amount);
        emit PostMintProxy();
    }
}
