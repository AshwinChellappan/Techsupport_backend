import os
import io
import re 
from PyPDF2 import PdfReader
from typing import Dict
import datetime
from .custom_logger import custom_logging
import html


MAX_SECTION_LENGTH = 5000
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 0

global verbose
verbose = int(os.getenv("VERBOSE_FLAG"))
global localpdfparser
localpdfparser = int(os.getenv("LOCALPDFPARSER_FLAG"))
global category
category = None


def get_mok_fileObject(bytes_content):
    mokfileObj = io.BytesIO()
    mokfileObj.write(bytes_content)
    mokfileObj.seek(0)
    return mokfileObj

def blob_name_from_file_page(filename, page=0):
    filename = os.path.basename(filename)
    file_prefix = os.path.splitext(os.path.basename(filename))[0]
    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension == ".pdf": return file_prefix + f"-{page}" + ".pdf"
    elif file_extension == ".xlsx": return  file_prefix+ f"-{page}" + ".xlsx"
    elif file_extension == ".csv": return  file_prefix+ f"-{page}" + ".csv"
    elif file_extension == ".txt": return  file_prefix+ f"-{page}" + ".txt"
    else: return os.path.basename(filename)

def table_to_html(table):
    table_html = "<table>"
    rows = [sorted([cell for cell in table.cells if cell.row_index == i],
                   key=lambda cell: cell.column_index) for i in range(table.row_count)]
    for row_cells in rows:
        table_html += "<tr>"
        for cell in row_cells:
            tag = "th" if (
                cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
            cell_spans = ""
            if cell.column_span > 1:
                cell_spans += f" colSpan={cell.column_span}"
            if cell.row_span > 1:
                cell_spans += f" rowSpan={cell.row_span}"
            table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
        table_html += "</tr>"
    table_html += "</table>"
    return table_html

def get_document_text(filename, content, client):
    offset = 0
    page_map = []
    if localpdfparser:
        reader = PdfReader(filename)
        pages = reader.pages
        for page_num, p in enumerate(pages):
            page_text = p.extract_text()
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)
    else:
        if verbose:
            custom_logging(f"Extracting text from '{filename}' using Azure Form Recognizer")
        form_recognizer_client = client
        # Create mok file object using io
        mokfileObj = get_mok_fileObject(content)
        # Reading file with form recognizer
        poller = form_recognizer_client.begin_analyze_document(
            "prebuilt-layout", document=mokfileObj)
        form_recognizer_results = poller.result()

        for page_num, page in enumerate(form_recognizer_results.pages):
            tables_on_page = [table for table in form_recognizer_results.tables if table.bounding_regions[0].page_number == page_num + 1]

            # mark all positions of the table spans in the page
            page_offset = page.spans[0].offset
            page_length = page.spans[0].length
            table_chars = [-1] * page_length
            for table_id, table in enumerate(tables_on_page):
                for span in table.spans:
                    # replace all table spans with "table_id" in table_chars
                    # array
                    for i in range(span.length):
                        idx = span.offset - page_offset + i
                        if idx >= 0 and idx < page_length:
                            table_chars[idx] = table_id

            # build page text by replacing charcters in table spans with table
            # html
            page_text = ""
            added_tables = set()
            for idx, table_id in enumerate(table_chars):
                if table_id == -1:
                    page_text += form_recognizer_results.content[page_offset + idx]
                elif table_id not in added_tables:
                    page_text += table_to_html(tables_on_page[table_id])
                    added_tables.add(table_id)

            page_text += " "
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)

    return page_map

def split_text(page_map, filename):
    SENTENCE_ENDINGS = [".", "!", "?"]
    WORDS_BREAKS = [",", ";", ":", " ",
                    "(", ")", "[", "]", "{", "}", "\t", "\n"]
    if verbose:
        custom_logging(f"Splitting '{filename}' into sections")

    def find_page(offset):
        l = len(page_map)
        for i in range(l - 1):
            if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
                return i
        return l - 1

    all_text = "".join(p[2] for p in page_map)
    length = len(all_text)
    start = 0
    end = length
    while start + SECTION_OVERLAP < length:
        last_word = -1
        end = start + MAX_SECTION_LENGTH

        if end > length:
            end = length
        else:
            # Try to find the end of the sentence
            while end < length and (
                    end -
                    start -
                    MAX_SECTION_LENGTH) < SENTENCE_SEARCH_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
                if all_text[end] in WORDS_BREAKS:
                    last_word = end
                end += 1
            if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                end = last_word  # Fall back to at least keeping a whole word
        if end < length:
            end += 1

        # Try to find the start of the sentence or at least a whole word
        # boundary
        last_word = -1
        while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * \
                SENTENCE_SEARCH_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
            if all_text[start] in WORDS_BREAKS:
                last_word = start
            start -= 1
        if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
            start = last_word
        if start > 0:
            start += 1

        section_text = all_text[start:end]
        # custom_logging("text for a section ",section_text)
        yield (section_text, find_page(start))

        last_table_start = section_text.rfind("<table")
        if (last_table_start > 2 * SENTENCE_SEARCH_LIMIT and last_table_start >
                section_text.rfind("</table")):
            # If the section ends with an unclosed table, we need to start the next section with the table.
            # If table starts inside SENTENCE_SEARCH_LIMIT, we ignore it, as that will cause an infinite loop for tables longer than MAX_SECTION_LENGTH
            # If last table starts inside SECTION_OVERLAP, keep overlapping
            if verbose:
                custom_logging(
                    f"Section ends with unclosed table, starting next section with the table at page {find_page(start)} offset {start} table start {last_table_start}")
            start = min(end - SECTION_OVERLAP, start + last_table_start)
        else:
            start = end - SECTION_OVERLAP

    if start + SECTION_OVERLAP < end:
        yield (all_text[start:end], find_page(start))

def get_all_text(filename, page_map):
    content = []
    for i, (section, pagenum) in enumerate(split_text(page_map, filename)):
        content.append(section)
    return " ".join(content)

def create_chunk_sections(filename, chunked_data, enc, groups: Dict,url:str):
    for i, chunk in enumerate(chunked_data):
        page_num = chunk.get('page_no')
        page_num = page_num if(page_num is not None) else i
        chunk_token_length = len(enc.encode(chunk.get('text','0')))
        # get page number by analyzing chunk data
        # page_number = get_page_for_chunk(chunk_text, page_map=page_map)
        #custom_logging(chunk)
    
        default_dict = {
            "id": re.sub("[^0-9a-zA-Z_-]", "_", f"{filename}-{i}"),
            "content": chunk.get('text','0'),
            "content_type": chunk['type'],
            "category": category,
            "group_ids": list(groups.values()),
            "group_names": list(groups.keys()),
            "url":url,
            "sourcechunk": blob_name_from_file_page(filename, page_num),
            "sourcefile": filename,
            "token_count": chunk_token_length, 
            "upload_ts": str(datetime.datetime.now())
        }
        price_list_dict = {'Description': chunk.get('Description'),
             'Item': chunk.get('Item'),
             'Model': chunk.get('Model'),
             'country_of_origin': chunk.get('country_of_origin'),
             'item_status': chunk.get('item_status'),
             'list_price': chunk.get('list_price'),
             'market_model': chunk.get('market_model'),
             'model_group': chunk.get('model_group'),
             'product_famly': chunk.get('product_famly')}

        price_list_dict = {key:str(val) for key,val in price_list_dict.items()}
        default_dict.update(price_list_dict)

        yield default_dict

def get_page_for_chunk(chunk, page_map):
    # get dictionary of page content
    page_number_by_content = {page[0]: page[-1] for page in page_map}
    for page_num, content in page_number_by_content.items():
        if chunk in content:
            return page_num
    return "NO_PAGE"
