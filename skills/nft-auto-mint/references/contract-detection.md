# Contract Type Detection Reference

## Quick Detection via Blockscout

```bash
curl -s --max-time 10 "https://eth.blockscout.com/api/v2/smart-contracts/0xCONTRACT" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('Name:', d.get('name'))
print('Verified:', d.get('is_verified'))
print('Proxy:', d.get('proxy_type'))
if d.get('implementations'):
    for i in d['implementations']:
        print('Impl:', i.get('address_hash'), '-', i.get('name'))
abi = json.loads(d.get('abi','[]')) if isinstance(d.get('abi'), str) else d.get('abi',[])
mint_funcs = [f['name'] for f in abi if f.get('type')=='function' and any(x in f.get('name','').lower() for x in ['mint','claim','buy','purchase'])]
print('Mint funcs:', mint_funcs)
"
```

## Common Contract Implementations

| Implementation Name | Ecosystem | Mint Function | Notes |
|---|---|---|---|
| `DropERC721` | Thirdweb | `claim()` | Struct params, see templates/mint-claim-thirdweb.js |
| `DropERC1155` | Thirdweb | `claim()` | Same pattern as DropERC721 |
| `ERC721SeaDropCloneable` | Seadrop/OpenSea | `mintSeaDrop()` | Simple 2-param |
| `ERC721SeaDrop` | Seadrop/OpenSea | `mintSeaDrop()` | Full version |
| `ERC721OpenSea` | OpenSea | `mintSeaDrop()` or custom | Check source |
| Custom OZ-based | Any | `mint()`, `mint(uint256)`, etc. | Check source |

## Function Selector Quick Reference

| Function | Selector |
|----------|----------|
| `mint()` | `0x1249c58b` |
| `mint(address)` | `0x40c10f19` |
| `mint(uint256)` | `0xa0712d68` |
| `mint(address,uint256)` | `0x40c10f19` (alias) |
| `safeMint(address,uint256)` | `0xa1448194` |
| `publicMint(address,uint256)` | `0x3a53acb0` |
| `claim()` (Thirdweb) | `0xd0b06f5d` (may vary by ABI) |
| `mintSeaDrop(address,uint256)` | Compute with `ethers.id("mintSeaDrop(address,uint256)")` |
| `price()` | `0xa035b1fe` |
| `cost()` | `0x590e1ae3` |
| `mintPrice()` | `0xb9bcc557` |
| `totalSupply()` | `0x18160ddd` |
| `totalMinted()` | `0xa2309ff8` |
| `maxSupply()` | `0xd5abeb01` |
| `MAX_SUPPLY()` | `0x32cb6b0c` |
| `hasMinted(address)` | `0x38e21cce` |
| `minted(address)` | `0x2b6f860f` |
| `balanceOf(address)` | `0x70a08231` |
| `name()` | `0x06fdde03` |
| `symbol()` | `0x95d89b41` |

## Thirdweb DropERC721 `claim()` Full Declaration

```solidity
function claim(
    address _receiver,
    uint256 _quantity,
    address _currency,
    uint256 _pricePerToken,
    AllowlistProof calldata _allowlistProof,
    bytes calldata _data
) external payable;
```

Where `AllowlistProof` is:
```solidity
struct AllowlistProof {
    bytes32[] proof;
    uint256 quantityLimitPerWallet;
    uint256 pricePerToken;
    address currency;
}
```

### Typical Values for Free Public Mint

| Parameter | Value |
|-----------|-------|
| `_currency` | `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` |
| `_pricePerToken` | `0` |
| `_allowlistProof.proof` | `[]` (empty array) |
| `_allowlistProof.quantityLimitPerWallet` | Max from claim condition (e.g. 7) |
| `_allowlistProof.pricePerToken` | `0` |
| `_allowlistProof.currency` | `0x0000000000000000000000000000000000000000` |
| `_data` | `0x` |

## Healthy Contract Detection

Signs of a legitimate project:
- [x] Verified on Etherscan with readable source code
- [x] Implementation contract also verified
- [x] Has social media / community presence
- [x] Non-trivial contract logic (not just a clone with renamed symbols)
- [x] Reasonable supply (not suspiciously high)

Red flags:
- [ ] Unverified contract
- [ ] Impossible claim conditions (mint $1000 worth but "free")
- [ ] Owner can change mint price at any time (setPrice function)
- [ ] No community, no website, no Twitter
- [ ] Cloneable pattern with no custom logic
