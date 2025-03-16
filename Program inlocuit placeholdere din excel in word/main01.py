import openpyxl
from docxtpl import DocxTemplate

# Load data from Excel
path = "d:\\Python\\print\\data01.xlsx"
workbook = openpyxl.load_workbook(path)
sheet = workbook.active

# Get the headers from the first row
headers = [cell.value for cell in sheet[1] if cell.value]  # Exclude empty cells
# Assume placeholders are surrounded by {{ and }}
placeholders = [f"{{{{ {header} }}}}" for header in headers]

# Generate docs
doc = DocxTemplate("template01.docx")

# Iterate over each row starting from the second row (skipping the headers)
for row in sheet.iter_rows(min_row=2, values_only=True):
    # Create a dictionary using headers as keys and row values as values
    data = dict(zip(headers, row))
    
    # Render the template
    doc.render(data)
    
  # Generate a document name based on student name and course
    doc_name = f"{data['crt']} {data['nume']} {data['autentic']}.docx"
    
    # Save the document
    doc.save(doc_name)

# Close the workbook
workbook.close()