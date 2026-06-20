// Simple `mint()` — no args, free or priced
// Usage: PK=0x... node mint-simple.js 0xCONTRACT_ADDRESS
const { ethers } = require("ethers");
const provider = new ethers.JsonRpcProvider("https://ethereum.publicnode.com");
const wallet = new ethers.Wallet(process.env.PK, provider);

async function run(contractAddr) {
  const contract = new ethers.Contract(contractAddr, [
    "function mint() payable",
    "function totalSupply() view returns (uint256)",
  ], wallet);

  const supply = await contract.totalSupply();
  console.log("Total supply:", supply.toString());

  const tx = await contract.mint({ value: 0, gasLimit: 200000 });
  console.log("Tx:", tx.hash);
  console.log("https://etherscan.io/tx/" + tx.hash);
  const receipt = await tx.wait();
  console.log("Status:", receipt.status === 1 ? "SUCCESS" : "FAILED");
  console.log("Gas:", receipt.gasUsed.toString());
}

run(process.argv[2]).catch(e => console.error("Error:", e.message.substring(0, 200)));
