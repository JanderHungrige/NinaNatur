<?xml version="1.0" encoding="UTF-8"?>
<!--
  One building from Bayern's LoD2 model, as the state publishes it: tile
  690_5334 of https://download1.bayernwolke.de/a/lod2/citygml/, fetched
  2026-09-20 and cut down to a single bldg:Building.

  Datenquelle: Bayerische Vermessungsverwaltung - www.geodaten.bayern.de,
  CC BY 4.0. Kept here because the claim "the NRW reader reads Bayern
  unchanged" is worth checking against a real file rather than one this
  repository wrote to its own expectations (doc 105).
-->
<core:CityModel xmlns:core="http://www.opengis.net/citygml/1.0"
                xmlns:bldg="http://www.opengis.net/citygml/building/1.0"
                xmlns:gen="http://www.opengis.net/citygml/generics/1.0"
                xmlns:gml="http://www.opengis.net/gml"
                xmlns:xlink="http://www.w3.org/1999/xlink">
<core:cityObjectMember>
<bldg:Building gml:id="DEBY_LOD2_59772">
<creationDate>2023-06-05</creationDate>
<externalReference>
<informationSystem>http://repository.gdi-de.org/schemas/adv/citygml/fdv/art.htm#_9100</informationSystem>
<externalObject>
<name>DEBYvAAAAABTy70E</name>
</externalObject>
</externalReference>
<gen:stringAttribute name="DatenquelleBodenhoehe">
<gen:value>1100</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="DatenquelleDachhoehe">
<gen:value>1000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="DatenquelleLage">
<gen:value>1000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Gemeindeschluessel">
<gen:value>09162000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="HoeheDach">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="HoeheGrund">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Methode">
<gen:value>2000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="NiedrigsteTraufeDesGebaeudes">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Grundrissaktualitaet">
<gen:value>2026-02-06</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Geometrietyp2DReferenz">
<gen:value>3000</gen:value>
</gen:stringAttribute>
<bldg:function>31001_9998</bldg:function>
<bldg:roofType>1000</bldg:roofType>
<bldg:measuredHeight uom="urn:adv:uom:m">11.715</bldg:measuredHeight>
<bldg:storeysAboveGround>3</bldg:storeysAboveGround>
<bldg:lod2Solid>
<gml:Solid srsDimension="3">
<gml:exterior>
<gml:CompositeSurface>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_4becb506-d53b-44ca-a483-e6a3d238b4c2_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_be3462c3-9865-467b-829d-76e6b9b692e7_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_c0aae462-3f4b-4062-80bb-8cd04768ab1a_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_a13e523a-7269-4637-88fa-e57eed6d9265_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_bacdfeda-2181-42c2-ac94-bf086ec95291_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_e76604b3-3834-4420-a1e5-c660f32ab045_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_c8be8650-e40d-4c7d-b491-d892085763aa_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_30ce7949-9c18-4a98-bdae-afeb9a0b6252_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_27c754d1-d65b-4b5e-a17a-8a24080009e1_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_bae63dbe-80b8-4e3a-a78e-755230366512_2_poly"/>
<gml:surfaceMember xlink:href="#DEBY_LOD2_59772_c21df86c-d952-4aa9-a5e2-42418b07a2a9_2_poly"/>
</gml:CompositeSurface>
</gml:exterior>
</gml:Solid>
</bldg:lod2Solid>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_4becb506-d53b-44ca-a483-e6a3d238b4c2_2">
<gen:stringAttribute name="Flaeche">
<gen:value>159.018</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_4becb506-d53b-44ca-a483-e6a3d238b4c2_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691478.01 5334825.81 516.71 691478.01 5334825.81 528.425 691473.38 5334813.05 528.425 691473.38 5334813.05 516.71 691478.01 5334825.81 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_be3462c3-9865-467b-829d-76e6b9b692e7_2">
<gen:stringAttribute name="Flaeche">
<gen:value>12.568</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_be3462c3-9865-467b-829d-76e6b9b692e7_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691474.24 5334826.79 516.71 691474.24 5334826.79 528.425 691475.29 5334827.01 528.425 691475.29 5334827.01 516.71 691474.24 5334826.79 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_c0aae462-3f4b-4062-80bb-8cd04768ab1a_2">
<gen:stringAttribute name="Flaeche">
<gen:value>4.854</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_c0aae462-3f4b-4062-80bb-8cd04768ab1a_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691472.46 5334820.87 516.71 691472.46 5334820.87 528.425 691472.6 5334821.26 528.425 691472.6 5334821.26 516.71 691472.46 5334820.87 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:RoofSurface gml:id="DEBY_LOD2_59772_a13e523a-7269-4637-88fa-e57eed6d9265_2">
<gen:stringAttribute name="Dachneigung">
<gen:value>90.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Dachorientierung">
<gen:value>-1.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Flaeche">
<gen:value>49.348</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_a13e523a-7269-4637-88fa-e57eed6d9265_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691470.72 5334813.99 528.425 691473.38 5334813.05 528.425 691478.01 5334825.81 528.425 691475.29 5334827.01 528.425 691474.24 5334826.79 528.425 691472.6 5334821.26 528.425 691472.46 5334820.87 528.425 691470.53 5334815.81 528.425 691470.29 5334815.2 528.425 691470.72 5334813.99 528.425</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:RoofSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_bacdfeda-2181-42c2-ac94-bf086ec95291_2">
<gen:stringAttribute name="Flaeche">
<gen:value>15.043</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_bacdfeda-2181-42c2-ac94-bf086ec95291_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691470.72 5334813.99 516.71 691470.72 5334813.99 528.425 691470.29 5334815.2 528.425 691470.29 5334815.2 516.71 691470.72 5334813.99 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_e76604b3-3834-4420-a1e5-c660f32ab045_2">
<gen:stringAttribute name="Flaeche">
<gen:value>7.679</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_e76604b3-3834-4420-a1e5-c660f32ab045_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691470.29 5334815.2 516.71 691470.29 5334815.2 528.425 691470.53 5334815.81 528.425 691470.53 5334815.81 516.71 691470.29 5334815.2 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_c8be8650-e40d-4c7d-b491-d892085763aa_2">
<gen:stringAttribute name="Flaeche">
<gen:value>33.050</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_c8be8650-e40d-4c7d-b491-d892085763aa_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691473.38 5334813.05 516.71 691473.38 5334813.05 528.425 691470.72 5334813.99 528.425 691470.72 5334813.99 516.71 691473.38 5334813.05 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_30ce7949-9c18-4a98-bdae-afeb9a0b6252_2">
<gen:stringAttribute name="Flaeche">
<gen:value>67.572</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_30ce7949-9c18-4a98-bdae-afeb9a0b6252_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691472.6 5334821.26 516.71 691472.6 5334821.26 528.425 691474.24 5334826.79 528.425 691474.24 5334826.79 516.71 691472.6 5334821.26 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_27c754d1-d65b-4b5e-a17a-8a24080009e1_2">
<gen:stringAttribute name="Flaeche">
<gen:value>34.828</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_27c754d1-d65b-4b5e-a17a-8a24080009e1_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691475.29 5334827.01 516.71 691475.29 5334827.01 528.425 691478.01 5334825.81 528.425 691478.01 5334825.81 516.71 691475.29 5334827.01 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:GroundSurface gml:id="DEBY_LOD2_59772_bae63dbe-80b8-4e3a-a78e-755230366512_2">
<gen:stringAttribute name="Flaeche">
<gen:value>49.348</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_bae63dbe-80b8-4e3a-a78e-755230366512_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691470.29 5334815.2 516.71 691470.53 5334815.81 516.71 691472.46 5334820.87 516.71 691472.6 5334821.26 516.71 691474.24 5334826.79 516.71 691475.29 5334827.01 516.71 691478.01 5334825.81 516.71 691473.38 5334813.05 516.71 691470.72 5334813.99 516.71 691470.29 5334815.2 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:GroundSurface>
</bldg:boundedBy>
<bldg:boundedBy>
<bldg:WallSurface gml:id="DEBY_LOD2_59772_c21df86c-d952-4aa9-a5e2-42418b07a2a9_2">
<gen:stringAttribute name="Flaeche">
<gen:value>63.443</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX">
<gen:value>11.715</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MAX_ASL">
<gen:value>528.425</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN">
<gen:value>0.000</gen:value>
</gen:stringAttribute>
<gen:stringAttribute name="Z_MIN_ASL">
<gen:value>516.710</gen:value>
</gen:stringAttribute>
<bldg:lod2MultiSurface>
<gml:MultiSurface srsDimension="3">
<gml:surfaceMember>
<gml:Polygon gml:id="DEBY_LOD2_59772_c21df86c-d952-4aa9-a5e2-42418b07a2a9_2_poly">
<gml:exterior>
<gml:LinearRing>
<gml:posList>691470.53 5334815.81 516.71 691470.53 5334815.81 528.425 691472.46 5334820.87 528.425 691472.46 5334820.87 516.71 691470.53 5334815.81 516.71</gml:posList>
</gml:LinearRing>
</gml:exterior>
</gml:Polygon>
</gml:surfaceMember>
</gml:MultiSurface>
</bldg:lod2MultiSurface>
</bldg:WallSurface>
</bldg:boundedBy>
</bldg:Building>
</core:cityObjectMember>
</core:CityModel>
