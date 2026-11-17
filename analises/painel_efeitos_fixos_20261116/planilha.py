import zipfile, math
import xml.etree.ElementTree as ET

def xlsx(path,abas):
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel='http://schemas.openxmlformats.org/package/2006/relationships'
    nsrel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    types='http://schemas.openxmlformats.org/package/2006/content-types'
    def xml(el):return ET.tostring(el,encoding='utf-8',xml_declaration=True)
    def colname(n):
        s=''
        while n:n,r=divmod(n-1,26);s=chr(65+r)+s
        return s
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        ct=ET.Element('Types',xmlns=types)
        ET.SubElement(ct,'Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
        ET.SubElement(ct,'Default',Extension='xml',ContentType='application/xml')
        for part,typ in [('workbook','sheet.main'),('styles','styles')]:
            ET.SubElement(ct,'Override',PartName=f'/xl/{part}.xml',ContentType=f'application/vnd.openxmlformats-officedocument.spreadsheetml.{typ}+xml')
        rootrels=ET.Element('Relationships',xmlns=rel)
        ET.SubElement(rootrels,'Relationship',Id='rId1',Type=nsrel+'/officeDocument',Target='xl/workbook.xml')
        z.writestr('_rels/.rels',xml(rootrels))
        wb=ET.Element('workbook',xmlns=ns);sheets=ET.SubElement(wb,'sheets');wbr=ET.Element('Relationships',xmlns=rel)
        styles=ET.Element('styleSheet',xmlns=ns)
        fonts=ET.SubElement(styles,'fonts',count='2')
        for bold in [False,True]:
            f=ET.SubElement(fonts,'font');ET.SubElement(f,'sz',val='11');ET.SubElement(f,'name',val='Calibri')
            if bold:ET.SubElement(f,'b')
        fills=ET.SubElement(styles,'fills',count='2')
        ET.SubElement(ET.SubElement(fills,'fill'),'patternFill',patternType='none')
        ET.SubElement(ET.SubElement(fills,'fill'),'patternFill',patternType='gray125')
        borders=ET.SubElement(styles,'borders',count='1');ET.SubElement(borders,'border')
        xfs=ET.SubElement(styles,'cellStyleXfs',count='1');ET.SubElement(xfs,'xf',numFmtId='0',fontId='0',fillId='0',borderId='0')
        xfs=ET.SubElement(styles,'cellXfs',count='2')
        ET.SubElement(xfs,'xf',numFmtId='0',fontId='0',fillId='0',borderId='0',xfId='0')
        ET.SubElement(xfs,'xf',numFmtId='0',fontId='1',fillId='0',borderId='0',xfId='0',applyFont='1')
        z.writestr('xl/styles.xml',xml(styles))
        for j,(nome,rows) in enumerate(abas.items(),1):
            ET.SubElement(sheets,'sheet',name=nome[:31],sheetId=str(j),attrib={f'{{{nsrel}}}id':f'rId{j}'})
            ET.SubElement(wbr,'Relationship',Id=f'rId{j}',Type=nsrel+'/worksheet',Target=f'worksheets/sheet{j}.xml')
            ET.SubElement(ct,'Override',PartName=f'/xl/worksheets/sheet{j}.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml')
            sh=ET.Element('worksheet',xmlns=ns)
            views=ET.SubElement(sh,'sheetViews');v=ET.SubElement(views,'sheetView',workbookViewId='0');ET.SubElement(v,'pane',ySplit='1',topLeftCell='A2',activePane='bottomLeft',state='frozen')
            cols=ET.SubElement(sh,'cols')
            for k in range(len(rows[0])):ET.SubElement(cols,'col',min=str(k+1),max=str(k+1),width='45' if k==0 else '22',customWidth='1')
            data=ET.SubElement(sh,'sheetData')
            for i,row in enumerate(rows,1):
                rr=ET.SubElement(data,'row',r=str(i))
                for k,value in enumerate(row,1):
                    if value is None:continue
                    numeric=isinstance(value,(int,float)) and not isinstance(value,bool)
                    cc=ET.SubElement(rr,'c',r=f'{colname(k)}{i}',s='1' if i==1 else '0',t='n' if numeric else 'inlineStr')
                    if numeric:ET.SubElement(cc,'v').text=str(value) if math.isfinite(value) else ''
                    else:ET.SubElement(ET.SubElement(cc,'is'),'t').text=str(value)
            ET.SubElement(sh,'autoFilter',ref=f'A1:{colname(len(rows[0]))}{len(rows)}')
            z.writestr(f'xl/worksheets/sheet{j}.xml',xml(sh))
        ET.SubElement(wbr,'Relationship',Id=f'rId{len(abas)+1}',Type=nsrel+'/styles',Target='styles.xml')
        z.writestr('xl/workbook.xml',xml(wb));z.writestr('xl/_rels/workbook.xml.rels',xml(wbr));z.writestr('[Content_Types].xml',xml(ct))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for n in z.namelist():ET.fromstring(z.read(n))
