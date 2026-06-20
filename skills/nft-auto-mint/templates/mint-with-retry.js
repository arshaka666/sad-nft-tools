// Competitive free mint — block limit retry + priority fee bidding
// Usage: PK=0x... node mint-with-retry.js 0xCONTRACT_ADDRESS [priority_gwei] [max_blocks]
const { ethers } = require("ethers");
const provider = new ethers.JsonRpcProvider("https://ethereum.publicnode.com");
const wallet = new ethers.Wallet(process.env.PK, provider);

const CONTRACT = process.argv[2];
const PRIORITY_GWEI = parseFloat(process.argv[3] || "1.5");
const MAX_BLOCKS = parseInt(process.argv[4] || "20");
const MINT_DATA = "0x1249c58b"; // mint() selector — change if different

async function run() {
  let currentBlock = await provider.getBlockNumber();
  console.log(`Block: ${currentBlock} | Priority: ${PRIORITY_GWEI} gwei`);
  console.log(`Waiting for block slot (max ${MAX_BLOCKS} blocks)...\n`);

  for (let attempt = 0; attempt < MAX_BLOCKS; attempt++) {
    // Wait for new block
    while (true) {
      await new Promise(r => setTimeout(r, 2000));
      const nb = await provider.getBlockNumber();
      if (nb > currentBlock) { currentBlock = nb; break; }
    }

    const block = await provider.getBlock(currentBlock, false);
    const baseFee = block.baseFeePerGas;
    const priority = ethers.parseUnits(String(PRIORITY_GWEI), "gwei");
    const maxFee = baseFee + priority;
    const nonce = await provider.getTransactionCount(wallet.address);

    try {
      const signed = await wallet.signTransaction({
        to: CONTRACT, data: MINT_DATA, value: "0x0",
        gasLimit: "0x30D40",
        maxPriorityFeePerGas: "0x" + priority.toString(16),
        maxFeePerGas: "0x" + maxFee.toString(16),
        chainId: 1, type: 2, nonce,
      });
      const sent = await provider.broadcastTransaction(signed);
      console.log(`Block ${currentBlock}: tx ${sent.hash}`);
      const receipt = await sent.wait(2, 60000);
      if (receipt.status === 1) {
        console.log(`\n✅ SUCCESS! Gas: ${receipt.gasUsed.toString()}`);
        console.log(`https://etherscan.io/tx/${sent.hash}`);
        return;
      }
      process.stdout.write(`Block ${currentBlock}: reverted, retrying...\r`);
    } catch (e) {
      process.stdout.write(`Block ${currentBlock}: error, retrying...      \r`);
    }
  }
  console.log(`\n❌ Failed after ${MAX_BLOCKS} blocks`);
}

run().catch(e => console.error("Error:", e.message.substring(0, 200)));
