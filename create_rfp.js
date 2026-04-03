const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
        AlignmentType, WidthType, BorderStyle, ShadingType, HeadingLevel } = require('docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: "Arial", size: 22 }
      }
    },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F4E78" },
        paragraph: { spacing: { before: 240, after: 120 } }
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E5C8A" },
        paragraph: { spacing: { before: 180, after: 100 } }
      }
    ]
  },
  sections: [{
    properties: {
      page: {
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("REQUEST FOR PROPOSAL (RFP)")]
      }),
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Enterprise Cloud Migration Services")]
      }),
      new Paragraph({
        text: "",
        spacing: { after: 120 }
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Issued by:" }), new TextRun(" Global Tech Solutions Inc.")]
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Date:" }), new TextRun(" January 15, 2024")]
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Proposal Due Date:" }), new TextRun(" February 15, 2024")]
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Decision Date:" }), new TextRun(" March 1, 2024")]
      }),
      new Paragraph({
        text: "",
        spacing: { after: 240 }
      }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("1. EXECUTIVE SUMMARY")]
      }),
      new Paragraph({
        text: "Global Tech Solutions Inc. is seeking a qualified vendor to support the migration and modernization of our enterprise IT infrastructure to cloud-based solutions. We currently operate on-premise data centers with legacy applications and require a comprehensive cloud transformation strategy.",
        spacing: { after: 120 }
      }),
      new Paragraph({
        text: "The scope includes infrastructure assessment, cloud platform selection, migration planning, and execution support with minimal business disruption.",
        spacing: { after: 240 }
      }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("2. BUSINESS BACKGROUND")]
      }),
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Organization: Global Tech Solutions Inc.")]
      }),
      new Paragraph({
        text: "Industry: Financial Services & Technology",
        spacing: { after: 120 }
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Current State:" })]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("500+ employees across 3 locations")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Legacy on-premise infrastructure (15+ years old)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("50+ applications (mix of custom and commercial)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("10TB+ of data requiring migration")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Annual IT budget: $2.5M")],
        spacing: { after: 120 }
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Business Drivers:" })]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Reduce capital expenditure on infrastructure")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Improve system reliability and uptime (current SLA: 99.2%, target: 99.95%)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Enable faster deployment of new applications")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Improve disaster recovery capabilities")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Modernize technology stack")],
        spacing: { after: 240 }
      }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("3. SCOPE OF WORK")]
      }),
      new Paragraph({
        text: "The vendor shall provide the following services:",
        spacing: { after: 120 }
      }),
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Phase 1: Assessment & Planning (Months 1-2)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Current infrastructure audit")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Application portfolio analysis")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Cloud readiness assessment")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Risk assessment")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Migration roadmap development")],
        spacing: { after: 120 }
      }),

      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Phase 2: Infrastructure Design (Month 2-3)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Cloud architecture design (multi-cloud or single cloud)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Security and compliance design")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Network design and connectivity")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Disaster recovery strategy")],
        spacing: { after: 120 }
      }),

      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Phase 3: Migration Execution (Months 4-8)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Infrastructure provisioning in cloud")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Application migration (prioritized waves)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Data migration and validation")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Testing and UAT support")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Cutover and go-live management")],
        spacing: { after: 120 }
      }),

      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: [new TextRun("Phase 4: Optimization & Support (Months 9-12)")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Performance optimization")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Cost optimization")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Knowledge transfer and training")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("90-day post-implementation support")],
        spacing: { after: 240 }
      }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("4. MANDATORY REQUIREMENTS")]
      }),
      new Paragraph({
        text: "Vendors must meet ALL of the following to be considered:",
        spacing: { after: 120 }
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("ISO 27001 Certification "), new TextRun({ italics: true, text: "- Information Security Management" })]
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("Cloud Platform Experience "), new TextRun({ italics: true, text: "- Minimum 5 years with AWS, Azure, or GCP" })]
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("Financial Services Experience "), new TextRun({ italics: true, text: "- At least 3 completed projects in financial services" })]
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("Dedicated Account Manager "), new TextRun({ italics: true, text: "- Full-time primary contact throughout engagement" })]
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("24/7 Support Availability "), new TextRun({ italics: true, text: "- Support team available 24 hours, 7 days a week" })]
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("SLA Guarantee "), new TextRun({ italics: true, text: "- Minimum 99.9% uptime guarantee" })]
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("Performance Bond "), new TextRun({ italics: true, text: "- Performance bond equal to 10% of contract value" })]
      }),
      new Paragraph({
        numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("Team Certifications "), new TextRun({ italics: true, text: "- At least 10 cloud architects with advanced certifications" })],
        spacing: { after: 240 }
      }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("5. EVALUATION CRITERIA")]
      }),
      new Paragraph({
        text: "Proposals will be evaluated on the following criteria:",
        spacing: { after: 120 }
      }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [4680, 4680],
        rows: [
          new TableRow({
            children: [
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun({ bold: true, text: "Criteria" })] })]
              }),
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun({ bold: true, text: "Weight" })] })]
              })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun("Technical Capability & Approach")] })]
              }),
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun("40%")] })]
              })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun("Cost & Commercial Terms")] })]
              }),
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun("30%")] })]
              })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun("Experience & References")] })]
              }),
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun("20%")] })]
              })
            ]
          }),
          new TableRow({
            children: [
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun("Team & Staffing")] })]
              }),
              new TableCell({
                borders,
                width: { size: 4680, type: WidthType.DXA },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun("10%")] })]
              })
            ]
          })
        ]
      }),
      new Paragraph({ text: "", spacing: { after: 240 } }),

      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: [new TextRun("6. BUDGET & PRICING")]
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Estimated Budget Range:" }), new TextRun(" $750,000 - $1,500,000")]
      }),
      new Paragraph({
        text: "",
        spacing: { after: 120 }
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Payment Terms:" })]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("20% upon contract signature")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("30% upon completion of Phase 1")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("30% upon completion of Phase 3")]
      }),
      new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("20% upon completion of Phase 4")],
        spacing: { after: 120 }
      }),
      new Paragraph({
        children: [new TextRun({ bold: true, text: "Preferred Pricing Model:" }), new TextRun(" Fixed price with time & materials for change orders")]
      })
    ]
  }],
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          {
            level: 0,
            format: "bullet",
            text: "•",
            alignment: AlignmentType.LEFT,
            style: {
              paragraph: {
                indent: { left: 720, hanging: 360 }
              }
            }
          }
        ]
      },
      {
        reference: "numbers",
        levels: [
          {
            level: 0,
            format: "decimal",
            text: "%1.",
            alignment: AlignmentType.LEFT,
            style: {
              paragraph: {
                indent: { left: 720, hanging: 360 }
              }
            }
          }
        ]
      }
    ]
  }
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("SAMPLE_RFP.docx", buffer);
  console.log("SAMPLE_RFP.docx created successfully!");
});
