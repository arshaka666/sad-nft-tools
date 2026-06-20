// Seadrop ERC721SeaDropCloneable mint
// Usage: PK=0x... node mint-seadrop.js 0xCONTRACT_ADDRESS [quantity]
const { ethers } = require("ethers");
const provider = new ethers.JsonRpcProvider("https://ethereum.publicnode.com");
const wallet = new ethers.Wallet(process.env.PK, provider);

const ABI = [
  "function mintSeaDrop(address minter, uint256 quantity) payable",
  "function name() view returns (string)",
  "function totalSupply() view returns (uint256)",
];

async function run(contractAddr, quantity) {
  const contract = new ethers.Contract(contractAddr, ABI, wallet);
  const name = await contract.name();
  const supply = await contract.totalSupply();
  console.log(`Contract: ${name}`);
  console.log(`Supply: ${supply.toString()}`);

  const tx = await contract.mintSeaDrop(wallet.address, quantity, { gasLimit: 200000 });
  console.log("Tx:", tx.hash);
  console.log("https://etherscan.io/tx/" + tx.hash);
  const receipt = await tx.wait();
  console.log("Status:", receipt.status === 1 ? "SUCCESS" : "FAILED");
  console.log("Gas:", receipt.gasUsed.toString());
}

const addr = process.argv[2];
const qty = parseInt(process.argv[3] || "1");
run(addr, qty).catch(e => console.error("Error:", e.message.substring(0, 200)));
