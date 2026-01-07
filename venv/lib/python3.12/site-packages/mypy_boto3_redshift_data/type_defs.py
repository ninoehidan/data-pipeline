"""
Type annotations for redshift-data service type definitions.

[Documentation](https://youtype.github.io/boto3_stubs_docs/mypy_boto3_redshift_data/type_defs/)

Copyright 2025 Vlad Emelianov

Usage::

    ```python
    from mypy_boto3_redshift_data.type_defs import BatchExecuteStatementInputTypeDef

    data: BatchExecuteStatementInputTypeDef = ...
    ```
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from datetime import datetime

from .literals import ResultFormatStringType, StatementStatusStringType, StatusStringType

if sys.version_info >= (3, 12):
    from typing import NotRequired, TypedDict
else:
    from typing_extensions import NotRequired, TypedDict


__all__ = (
    "BatchExecuteStatementInputTypeDef",
    "BatchExecuteStatementOutputTypeDef",
    "CancelStatementRequestTypeDef",
    "CancelStatementResponseTypeDef",
    "ColumnMetadataTypeDef",
    "DescribeStatementRequestTypeDef",
    "DescribeStatementResponseTypeDef",
    "DescribeTableRequestPaginateTypeDef",
    "DescribeTableRequestTypeDef",
    "DescribeTableResponseTypeDef",
    "ExecuteStatementInputTypeDef",
    "ExecuteStatementOutputTypeDef",
    "FieldTypeDef",
    "GetStatementResultRequestPaginateTypeDef",
    "GetStatementResultRequestTypeDef",
    "GetStatementResultResponseTypeDef",
    "GetStatementResultV2RequestPaginateTypeDef",
    "GetStatementResultV2RequestTypeDef",
    "GetStatementResultV2ResponseTypeDef",
    "ListDatabasesRequestPaginateTypeDef",
    "ListDatabasesRequestTypeDef",
    "ListDatabasesResponseTypeDef",
    "ListSchemasRequestPaginateTypeDef",
    "ListSchemasRequestTypeDef",
    "ListSchemasResponseTypeDef",
    "ListStatementsRequestPaginateTypeDef",
    "ListStatementsRequestTypeDef",
    "ListStatementsResponseTypeDef",
    "ListTablesRequestPaginateTypeDef",
    "ListTablesRequestTypeDef",
    "ListTablesResponseTypeDef",
    "PaginatorConfigTypeDef",
    "QueryRecordsTypeDef",
    "ResponseMetadataTypeDef",
    "SqlParameterTypeDef",
    "StatementDataTypeDef",
    "SubStatementDataTypeDef",
    "TableMemberTypeDef",
)


class BatchExecuteStatementInputTypeDef(TypedDict):
    Sqls: Sequence[str]
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    Database: NotRequired[str]
    WithEvent: NotRequired[bool]
    StatementName: NotRequired[str]
    WorkgroupName: NotRequired[str]
    ClientToken: NotRequired[str]
    ResultFormat: NotRequired[ResultFormatStringType]
    SessionKeepAliveSeconds: NotRequired[int]
    SessionId: NotRequired[str]


class ResponseMetadataTypeDef(TypedDict):
    RequestId: str
    HTTPStatusCode: int
    HTTPHeaders: dict[str, str]
    RetryAttempts: int
    HostId: NotRequired[str]


class CancelStatementRequestTypeDef(TypedDict):
    Id: str


class ColumnMetadataTypeDef(TypedDict):
    isCaseSensitive: NotRequired[bool]
    isCurrency: NotRequired[bool]
    isSigned: NotRequired[bool]
    label: NotRequired[str]
    name: NotRequired[str]
    nullable: NotRequired[int]
    precision: NotRequired[int]
    scale: NotRequired[int]
    schemaName: NotRequired[str]
    tableName: NotRequired[str]
    typeName: NotRequired[str]
    length: NotRequired[int]
    columnDefault: NotRequired[str]


class DescribeStatementRequestTypeDef(TypedDict):
    Id: str


class SqlParameterTypeDef(TypedDict):
    name: str
    value: str


class SubStatementDataTypeDef(TypedDict):
    Id: str
    Duration: NotRequired[int]
    Error: NotRequired[str]
    Status: NotRequired[StatementStatusStringType]
    CreatedAt: NotRequired[datetime]
    UpdatedAt: NotRequired[datetime]
    QueryString: NotRequired[str]
    ResultRows: NotRequired[int]
    ResultSize: NotRequired[int]
    RedshiftQueryId: NotRequired[int]
    HasResultSet: NotRequired[bool]


class PaginatorConfigTypeDef(TypedDict):
    MaxItems: NotRequired[int]
    PageSize: NotRequired[int]
    StartingToken: NotRequired[str]


class DescribeTableRequestTypeDef(TypedDict):
    Database: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    ConnectedDatabase: NotRequired[str]
    Schema: NotRequired[str]
    Table: NotRequired[str]
    NextToken: NotRequired[str]
    MaxResults: NotRequired[int]
    WorkgroupName: NotRequired[str]


class FieldTypeDef(TypedDict):
    isNull: NotRequired[bool]
    booleanValue: NotRequired[bool]
    longValue: NotRequired[int]
    doubleValue: NotRequired[float]
    stringValue: NotRequired[str]
    blobValue: NotRequired[bytes]


class GetStatementResultRequestTypeDef(TypedDict):
    Id: str
    NextToken: NotRequired[str]


class GetStatementResultV2RequestTypeDef(TypedDict):
    Id: str
    NextToken: NotRequired[str]


class QueryRecordsTypeDef(TypedDict):
    CSVRecords: NotRequired[str]


class ListDatabasesRequestTypeDef(TypedDict):
    Database: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    NextToken: NotRequired[str]
    MaxResults: NotRequired[int]
    WorkgroupName: NotRequired[str]


class ListSchemasRequestTypeDef(TypedDict):
    Database: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    ConnectedDatabase: NotRequired[str]
    SchemaPattern: NotRequired[str]
    NextToken: NotRequired[str]
    MaxResults: NotRequired[int]
    WorkgroupName: NotRequired[str]


class ListStatementsRequestTypeDef(TypedDict):
    NextToken: NotRequired[str]
    MaxResults: NotRequired[int]
    StatementName: NotRequired[str]
    Status: NotRequired[StatusStringType]
    RoleLevel: NotRequired[bool]
    Database: NotRequired[str]
    ClusterIdentifier: NotRequired[str]
    WorkgroupName: NotRequired[str]


class ListTablesRequestTypeDef(TypedDict):
    Database: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    ConnectedDatabase: NotRequired[str]
    SchemaPattern: NotRequired[str]
    TablePattern: NotRequired[str]
    NextToken: NotRequired[str]
    MaxResults: NotRequired[int]
    WorkgroupName: NotRequired[str]


TableMemberTypeDef = TypedDict(
    "TableMemberTypeDef",
    {
        "name": NotRequired[str],
        "type": NotRequired[str],
        "schema": NotRequired[str],
    },
)


class BatchExecuteStatementOutputTypeDef(TypedDict):
    Id: str
    CreatedAt: datetime
    ClusterIdentifier: str
    DbUser: str
    DbGroups: list[str]
    Database: str
    SecretArn: str
    WorkgroupName: str
    SessionId: str
    ResponseMetadata: ResponseMetadataTypeDef


class CancelStatementResponseTypeDef(TypedDict):
    Status: bool
    ResponseMetadata: ResponseMetadataTypeDef


class ExecuteStatementOutputTypeDef(TypedDict):
    Id: str
    CreatedAt: datetime
    ClusterIdentifier: str
    DbUser: str
    DbGroups: list[str]
    Database: str
    SecretArn: str
    WorkgroupName: str
    SessionId: str
    ResponseMetadata: ResponseMetadataTypeDef


class ListDatabasesResponseTypeDef(TypedDict):
    Databases: list[str]
    ResponseMetadata: ResponseMetadataTypeDef
    NextToken: NotRequired[str]


class ListSchemasResponseTypeDef(TypedDict):
    Schemas: list[str]
    ResponseMetadata: ResponseMetadataTypeDef
    NextToken: NotRequired[str]


class DescribeTableResponseTypeDef(TypedDict):
    TableName: str
    ColumnList: list[ColumnMetadataTypeDef]
    ResponseMetadata: ResponseMetadataTypeDef
    NextToken: NotRequired[str]


class ExecuteStatementInputTypeDef(TypedDict):
    Sql: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    Database: NotRequired[str]
    WithEvent: NotRequired[bool]
    StatementName: NotRequired[str]
    Parameters: NotRequired[Sequence[SqlParameterTypeDef]]
    WorkgroupName: NotRequired[str]
    ClientToken: NotRequired[str]
    ResultFormat: NotRequired[ResultFormatStringType]
    SessionKeepAliveSeconds: NotRequired[int]
    SessionId: NotRequired[str]


class StatementDataTypeDef(TypedDict):
    Id: str
    QueryString: NotRequired[str]
    QueryStrings: NotRequired[list[str]]
    SecretArn: NotRequired[str]
    Status: NotRequired[StatusStringType]
    StatementName: NotRequired[str]
    CreatedAt: NotRequired[datetime]
    UpdatedAt: NotRequired[datetime]
    QueryParameters: NotRequired[list[SqlParameterTypeDef]]
    IsBatchStatement: NotRequired[bool]
    ResultFormat: NotRequired[ResultFormatStringType]
    SessionId: NotRequired[str]


class DescribeStatementResponseTypeDef(TypedDict):
    Id: str
    SecretArn: str
    DbUser: str
    Database: str
    ClusterIdentifier: str
    Duration: int
    Error: str
    Status: StatusStringType
    CreatedAt: datetime
    UpdatedAt: datetime
    RedshiftPid: int
    HasResultSet: bool
    QueryString: str
    ResultRows: int
    ResultSize: int
    RedshiftQueryId: int
    QueryParameters: list[SqlParameterTypeDef]
    SubStatements: list[SubStatementDataTypeDef]
    WorkgroupName: str
    ResultFormat: ResultFormatStringType
    SessionId: str
    ResponseMetadata: ResponseMetadataTypeDef


class DescribeTableRequestPaginateTypeDef(TypedDict):
    Database: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    ConnectedDatabase: NotRequired[str]
    Schema: NotRequired[str]
    Table: NotRequired[str]
    WorkgroupName: NotRequired[str]
    PaginationConfig: NotRequired[PaginatorConfigTypeDef]


class GetStatementResultRequestPaginateTypeDef(TypedDict):
    Id: str
    PaginationConfig: NotRequired[PaginatorConfigTypeDef]


class GetStatementResultV2RequestPaginateTypeDef(TypedDict):
    Id: str
    PaginationConfig: NotRequired[PaginatorConfigTypeDef]


class ListDatabasesRequestPaginateTypeDef(TypedDict):
    Database: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    WorkgroupName: NotRequired[str]
    PaginationConfig: NotRequired[PaginatorConfigTypeDef]


class ListSchemasRequestPaginateTypeDef(TypedDict):
    Database: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    ConnectedDatabase: NotRequired[str]
    SchemaPattern: NotRequired[str]
    WorkgroupName: NotRequired[str]
    PaginationConfig: NotRequired[PaginatorConfigTypeDef]


class ListStatementsRequestPaginateTypeDef(TypedDict):
    StatementName: NotRequired[str]
    Status: NotRequired[StatusStringType]
    RoleLevel: NotRequired[bool]
    Database: NotRequired[str]
    ClusterIdentifier: NotRequired[str]
    WorkgroupName: NotRequired[str]
    PaginationConfig: NotRequired[PaginatorConfigTypeDef]


class ListTablesRequestPaginateTypeDef(TypedDict):
    Database: str
    ClusterIdentifier: NotRequired[str]
    SecretArn: NotRequired[str]
    DbUser: NotRequired[str]
    ConnectedDatabase: NotRequired[str]
    SchemaPattern: NotRequired[str]
    TablePattern: NotRequired[str]
    WorkgroupName: NotRequired[str]
    PaginationConfig: NotRequired[PaginatorConfigTypeDef]


class GetStatementResultResponseTypeDef(TypedDict):
    Records: list[list[FieldTypeDef]]
    ColumnMetadata: list[ColumnMetadataTypeDef]
    TotalNumRows: int
    ResponseMetadata: ResponseMetadataTypeDef
    NextToken: NotRequired[str]


class GetStatementResultV2ResponseTypeDef(TypedDict):
    Records: list[QueryRecordsTypeDef]
    ColumnMetadata: list[ColumnMetadataTypeDef]
    TotalNumRows: int
    ResultFormat: ResultFormatStringType
    ResponseMetadata: ResponseMetadataTypeDef
    NextToken: NotRequired[str]


class ListTablesResponseTypeDef(TypedDict):
    Tables: list[TableMemberTypeDef]
    ResponseMetadata: ResponseMetadataTypeDef
    NextToken: NotRequired[str]


class ListStatementsResponseTypeDef(TypedDict):
    Statements: list[StatementDataTypeDef]
    ResponseMetadata: ResponseMetadataTypeDef
    NextToken: NotRequired[str]
