import jsPDF from 'jspdf';

export function downloadPdf(title, sections) {
  const document = new jsPDF();
  let y = 18;
  document.setFontSize(18);
  document.text(title, 14, y);
  y += 10;
  document.setFontSize(10);
  sections.forEach(({ heading, body }) => {
    if (y > 270) {
      document.addPage();
      y = 18;
    }
    document.setFontSize(12);
    document.text(heading, 14, y);
    y += 6;
    document.setFontSize(9);
    const lines = document.splitTextToSize(String(body), 180);
    document.text(lines, 14, y);
    y += lines.length * 4 + 8;
  });
  document.save(`${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.pdf`);
}
