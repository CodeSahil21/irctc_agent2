const { PrismaClient } = require("@prisma/client");

console.log("Imported PrismaClient");

try {
  const prisma = new PrismaClient();
  console.log("Created PrismaClient successfully");
  prisma.$disconnect();
} catch (err) {
  console.error(err);
}
