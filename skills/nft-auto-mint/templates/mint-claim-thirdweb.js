// Thirdweb DropERC721 claim - handles claim() with allowlistProof struct
// Usage: PK=0x... node mint-claim-thirdweb.js 0xCONTRACT_ADDRESS [quantity] [priority_gwei]
const { ethers } = require("ethers");
const provider = new ethers.JsonRpcProvider("https://ethereum.publicnode.com");
const wallet = new ethers.Wallet(process.env.PK, provider);

const ABI = [
  "function claim(address _receiver, uint256 _quantity, address _currency, uint256 _pricePerToken, tuple(bytes32[] proof, uint256 quantityLimitPerWallet, uint256 pricePerToken, address currency) _allowlistProof, bytes _data) payable",
  "function name() view returns (string)",
  "function totalSupply() view returns (uint256)",
];

async function run(contractAddr, quantity, priorityGwei) {
  const contract = new ethers.Contract(contractAddr, ABI, wallet);
  const name = await contract.name();
  const supply = await contract.totalSupply();
  console.log(`Contract: ${name}`);
  console.log(`Supply: ${supply.toString()}`);
  
  const emptyProof = {
    proof: [],
    quantityLimitPerWallet: 7,
    pricePerToken: 0,
    currency: "0x0000000000000000000000000000000000000000"
  };

  const tx = await contract.claim(
    wallet.address,
    quantity,
    "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE", // ETH
    0, // free
    emptyProof,
    "0x",
    { value: 0, gasLimit: 200000 }
  );
  
  console.log("Tx:", tx.hash);
  console.log("https://etherscan.io/tx/" + tx.hash);
  const receipt = await tx.wait();
  console.log("Status:", receipt.status === 1 ? "SUCCESS" : "FAILED");
  console.log("Gas:", receipt.gasUsed.toString());
}

const addr = process.argv[2];
const qty = parseInt(process.argv[3] || "1");
run(addr, qty).catch(e => console.error("Error:", e.message.substring(0, 200)));
